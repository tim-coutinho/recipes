/* eslint-disable */
import {
  addCategory,
  addRecipe,
  deleteCategory,
  deleteRecipe,
  getAllCategories,
  getAllRecipes,
} from "./operations";

export default class Database {
  constructor(user, recipeListListener, categoryListListener) {
    if (user === null) {
      return;
    }
    this.recipes = {};
    this.categories = {};
    this.recipeListListener = recipeListListener;
    this.categoryListListener = categoryListListener;

    getAllRecipes().then(({ recipes }) => {
      recipes.forEach(recipe => (this.recipes[recipe.recipeId] = recipe));
      this.updateLocalDatabase(true, false);
    });
    getAllCategories().then(({ categories }) => {
      categories.forEach(category => (this.categories[category.categoryId] = category));
      this.updateLocalDatabase(false, true);
    });
  }

  updateLocalDatabase(recipes = true, categories = true) {
    recipes && this.recipeListListener(this.recipes);
    categories && this.categoryListListener(this.categories);
  }

  async addRecipe(values, recipeId = null) {
    delete values["recipeId"];
    delete values["lastEditedTime"];
    delete values["originalSubmitTime"];
    const res = await addRecipe(values, recipeId);
    if (!res) {
      return;
    }
    this.recipes[res.recipeId] = { ...this.recipes[res.recipeId], ...values, categories: [] };
    res.originalSubmitTime &&
      (this.recipes[res.recipeId].originalSubmitTime = res.originalSubmitTime);
    res.existingCategories &&
      (this.recipes[res.recipeId].categories = res.categories.map(category => category.categoryId));
    res.newCategories?.forEach(category => {
      this.recipes[res.recipeId].categories.push(category.categoryId);
      this.categories[category.categoryId] = category;
    });
    this.updateLocalDatabase();
  }

  async deleteRecipe(recipeId) {
    await deleteRecipe(recipeId);
    delete this.recipes[recipeId];
    this.updateLocalDatabase(true, false);
  }

  async addCategory(category, categoryId = null) {
    if (category in this.categories) {
      return;
    }
    const res = await addCategory(category, categoryId);
    if (!res) {
      return;
    }
    this.categories[res.categoryId] = {
      ...this.categories[res.categoryId],
      name: category,
    };
    this.updateLocalDatabase(false, true);
  }

  async deleteCategory(categoryId) {
    const res = await deleteCategory(categoryId);
    delete this.categories[categoryId];
    res?.updatedRecipes?.forEach(recipeId =>
      this.recipes[recipeId].categories.splice(
        this.recipes[recipeId].categories.findIndex(c => c === categoryId, 1)
      )
    );
    this.updateLocalDatabase();
  }
}
