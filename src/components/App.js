import { hot } from "react-hot-loader/root"; // Enable live component reloading
import React, { useEffect, useState } from "react";

import firebase, {auth, provider} from "../utils/firebase.js";

import AddForm from "./AddForm.js";
import Details from "./Details.js";
import Header from "./Header.js";
import RecipeList from "./RecipeList.js";
import Sidebar from "./Sidebar.js";

import "./App.scss";


function App() {
    const [user, setUser] = useState(auth.currentUser);
    const [items, setItems] = useState([]);
    const [filter, setFilter] = useState("");
    const [selectedRecipe, setSelectedRecipe] = useState("");
    const [filteredItems, setFilteredItems] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [currentView, setCurrentView] = useState("Home");
    const [categories, setCategories] = useState([]);
    const [selectedSidebarItem, setSelectedSidebarItem] = useState("All Recipes");
    const [editMode, setEditMode] = useState(false);

    const handleViewChange = (source) => {
        setCurrentView(() => {
            switch (source) {
            case "Edit":
                setEditMode(true);
                return currentView === "Add" ? "Home" : "Add";
            case "Add":
                setEditMode(false);
                return currentView === "Add" ? "Home" : "Add";
            case "Sidebar":
                return currentView === "Home" ? "Sidebar" : "Home";
            default:
                return "Home";
            }
        });
    };

    const handleAddRecipe = values => {
        if (values) {
            const [ingredients, instructions] = [{}, {}];
            for (const [i, element] of values.ingredients.entries()) {
                ingredients[i] = element;
            }
            for (const [i, element] of values.instructions.entries()) {
                instructions[i] = element;
            }
            const itemsRef = firebase.ref(`users/${user.uid}/recipes`);
            if ("id" in values) {
                itemsRef.child(values.id).set({
                    ...values,
                    ingredients,
                    instructions,
                    id: null
                });
            } else {
                itemsRef.push({
                    ...values,
                    ingredients,
                    instructions,
                    id: null
                });
            }
        }
        handleViewChange("Add");
    };

    const handleListChange = snapshot => {
        setIsLoading(true);
        setItems(snapshot.val());
    };

    const handleFilterChange = ({target}) => {
        setFilter(target.value);
    };

    useEffect(() => {
        const categories = [{name: "All Recipes", selected: true}];
        for (const [, item] of Object.entries(items)) {
            if (item.categories) {
                Object.values(item.categories)
                    .forEach(category => categories.push({name: category, selected: false}));
            }
        }
        setCategories(categories);
        setFilteredItems(Object.entries(items).filter(([, item]) => item.name.toLowerCase().includes(filter.toLowerCase())));
    }, [filter, items]);

    useEffect(() => {
        setIsLoading(false);
    }, [filteredItems, items]);

    useEffect(() => {
        if (!user) {
            return;
        }
        const itemsRef = firebase.ref(`users/${user.uid}/recipes`);
        itemsRef.on("value", handleListChange);
        itemsRef.on("child_removed", handleListChange);
    }, [user]);

    useEffect(() => {
        auth.onAuthStateChanged(user => {
            if (user) {
                setUser(user);
            } else {
                auth.signInWithRedirect(provider);
                auth.getRedirectResult().then(result => {
                    setUser(result.user);
                });
            }
        });
    }, []);

    return (
        <div id="app">
            <Sidebar
                categories={categories}
                changeSelectedItem={setSelectedSidebarItem}
                selectedItem={selectedSidebarItem}
                classes={currentView === "Add" ? "disabled" : ""}
            />
            <div
                id="main-content"
                className={`${currentView === "Sidebar" ? "shifted-right" : currentView === "Add" ? "disabled" : ""}`}
            >
                <div id="left">
                    <Header
                        filter={filter}
                        shiftedRight={currentView === "Sidebar"}
                        handleFilterChange={handleFilterChange}
                        handleViewChange={handleViewChange}
                    />
                    <RecipeList
                        items={isLoading ? null : filteredItems}
                        changeSelectedRecipe={(id) => setSelectedRecipe(id)}
                        selectedCategory={selectedSidebarItem}
                        selectedRecipe={selectedRecipe}
                        handleViewChange={handleViewChange}
                    />
                </div>
                <div id="right">
                    <Details
                        item={items[selectedRecipe]}
                        edit={() => handleViewChange("Edit")}
                    />
                </div>
            </div>
            <AddForm
                handleAddRecipe={handleAddRecipe}
                visible={currentView === "Add"}
                initialValues={editMode ? {id: selectedRecipe, ...items[selectedRecipe]} : {}}
            />
        </div>
    );
}

export default hot(App);
