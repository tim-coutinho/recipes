import os
from math import floor
from time import time
from typing import Final, Mapping

import boto3
from boto3_type_annotations.cognito_idp import Client as CognitoClient
from botocore.exceptions import ParamValidationError

from lib.common import get_meta_table, pformat_ as pformat, root_logger, verify_parameters
from lib.types import Response, ResponseData

logging = root_logger.getChild("auth")

CLIENT_ID: Final[str] = os.environ.get("client_id")
USER_POOL_ID: Final[str] = os.environ.get("user_pool_id")


def sign_up(body: Mapping[str, str]) -> Response:
    """
    Sign up using email and password.

    :param body: Mapping containing email and password keys
    :return: (Response specifics, status code)(Response specifics, status code)
    """
    logging.info("Starting sign up flow.")
    email, password = verify_parameters(body, "email", "password")

    client: CognitoClient = boto3.client("cognito-idp")
    try:
        res = client.sign_up(ClientId=CLIENT_ID, Username=email, Password=password)
    except client.exceptions.UsernameExistsException:
        logging.exception("")
        return ResponseData(message="This email is already registered.", exception=True), 409
    except (client.exceptions.InvalidPasswordException, ParamValidationError):
        logging.exception("")
        return ResponseData(message="Invalid password.", exception=True), 400
    except Exception:
        logging.exception("")
        return ResponseData(message="Unexpected exception encountered.", exception=True), 500

    logging.info(f"Sign up response:\n{pformat(res)}")
    meta_table, _ = get_meta_table()

    meta_table.put_item(
        Item={
            "userId": res["UserSub"],
            "signUpTime": floor(time() * 1000),
        }
    )

    logging.info("Sign up flow successful.")
    return (
        ResponseData(message=f"Sign up successful! A verification email has been sent to {email}."),
        200,
    )


def confirm_sign_up(body: Mapping[str, str]) -> Response:
    """
    Confirm sign up using a confirmation code.

    :param body: Mapping containing email and confirmationCode keys
    :return: (Response specifics, status code)
    """
    logging.info("Starting confirm sign up flow.")
    email, confirmation_code = verify_parameters(body, "email", "confirmationCode")

    client: CognitoClient = boto3.client("cognito-idp")
    try:
        client.confirm_sign_up(
            ClientId=CLIENT_ID,
            Username=email,
            ConfirmationCode=confirmation_code,
        )
    except client.exceptions.UserNotFoundException:
        logging.exception("")
        return ResponseData(message="This email is not registered.", exception=True), 404
    except (client.exceptions.CodeMismatchException, ParamValidationError):
        logging.exception("")
        return ResponseData(message="Invalid confirmation code.", exception=True), 400
    except client.exceptions.NotAuthorizedException:
        logging.exception("")
        return ResponseData(message="User has already been verified.", exception=True), 400
    except Exception:
        logging.exception("")
        return ResponseData(message="Unexpected exception encountered.", exception=True), 500

    logging.info("Confirm sign up flow successful.")
    return ResponseData(message="Your email has been verified!"), 200


def sign_in(body: Mapping[str, str]) -> Response:
    """
    Sign in using email and password.

    :param body: Mapping containing email and password keys
    :return: (Response specifics, status code)
    """
    logging.info("Starting sign in flow.")
    email, password = verify_parameters(body, "email", "password")

    client: CognitoClient = boto3.client("cognito-idp")

    try:
        res = client.admin_initiate_auth(
            AuthFlow="ADMIN_USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": email, "PASSWORD": password},
            ClientId=CLIENT_ID,
            UserPoolId=USER_POOL_ID,
        )
    except client.exceptions.NotAuthorizedException:
        logging.exception("")
        return ResponseData(message="Incorrect password.", exception=True), 401
    except client.exceptions.UserNotConfirmedException:
        logging.exception("")
        return ResponseData(message="User is not verified.", exception=True), 403
    except client.exceptions.UserNotFoundException:
        logging.exception("")
        return ResponseData(message="This email is not registered.", exception=True), 404
    except Exception:
        logging.exception("")
        return ResponseData(message="Unexpected exception encountered.", exception=True), 500

    res = res["AuthenticationResult"]
    access_token = res.get("AccessToken")
    refresh_token = res.get("RefreshToken")
    id_token = res.get("IdToken")

    user = client.get_user(AccessToken=access_token).get("Username")

    logging.info("Sign in flow successful.")
    return (
        ResponseData(
            message="You have been signed in.",
            data={"idToken": id_token, "refreshToken": refresh_token, "user": user},
        ),
        200,
    )


def refresh_id_token(body: Mapping[str, str]) -> Response:
    """
    Refresh a user's ID token using a refresh token.

    :param body: Mapping containing a refreshToken key
    :return: (Response specifics, status code)
    """
    logging.info("Starting refresh ID token flow.")
    (refresh_token,) = verify_parameters(body, "refreshToken")

    client: CognitoClient = boto3.client("cognito-idp")

    try:
        res = client.admin_initiate_auth(
            AuthFlow="REFRESH_TOKEN_AUTH",
            AuthParameters=({"REFRESH_TOKEN": refresh_token}),
            ClientId=CLIENT_ID,
            UserPoolId=USER_POOL_ID,
        )
    except client.exceptions.NotAuthorizedException:
        logging.exception("")
        return (
            ResponseData(
                message="Invalid refresh token.", data={"refreshTokenExpired": True}, exception=True
            ),
            401,
        )
    except client.exceptions.UserNotConfirmedException:
        logging.exception("")
        return ResponseData(message="User is not verified.", exception=True), 403
    except Exception:
        logging.exception("")
        return ResponseData(message="Unexpected exception encountered.", exception=True), 500

    res = res["AuthenticationResult"]
    access_token = res.get("AccessToken")
    id_token = res.get("IdToken")

    user = client.get_user(AccessToken=access_token).get("Username")

    logging.info("Refresh ID token flow successful.")
    return (
        ResponseData(message="You have been signed in.", data={"idToken": id_token, "user": user}),
        200,
    )


def resend_code(body: Mapping[str, str]) -> Response:
    """
    Resend a confirmation code to a user's email.

    :param body: Mapping containing an email key
    :return: (Response specifics, status code)
    """
    logging.info("Starting resend code flow.")
    (email,) = verify_parameters(body, "email")

    client: CognitoClient = boto3.client("cognito-idp")
    try:
        client.resend_confirmation_code(ClientId=CLIENT_ID, Username=email)
    except client.exceptions.UserNotFoundException:
        logging.exception("")
        return ResponseData(message="This email is not registered.", exception=True), 404
    except client.exceptions.InvalidParameterException:
        logging.exception("")
        return ResponseData(message="User is already verified.", exception=True), 400
    except Exception:
        logging.exception("")
        return ResponseData(message="Unexpected exception encountered.", exception=True), 500

    logging.info("Resend code flow successful.")
    return ResponseData(message=f"A verification code has been sent to {email}."), 200


def forgot_password(body: Mapping[str, str]) -> Response:
    """
    Send a forgot password email to a user.

    :param body: Mapping containing an email key
    :return: (Response specifics, status code)
    """
    logging.info("Starting forgot password flow.")
    (email,) = verify_parameters(body, "email")

    client: CognitoClient = boto3.client("cognito-idp")
    try:
        client.forgot_password(ClientId=CLIENT_ID, Username=email)
    except client.exceptions.UserNotFoundException:
        logging.exception("")
        return ResponseData(message="This email is not registered.", exception=True), 404
    except client.exceptions.InvalidParameterException:
        logging.exception("")
        return ResponseData(message="User is not verified yet.", exception=True), 403
    except Exception:
        logging.exception("")
        return ResponseData(message="Unexpected exception encountered.", exception=True), 500

    logging.info("Forgot password flow successful.")
    return ResponseData(message=f"A password reset code has been sent to {email}."), 200


def confirm_forgot_password(body: Mapping[str, str]) -> Response:
    """
    Reset a user's password using a confirmation code and a new password.

    :param body: Mapping containing email, password, and confirmationCode keys
    :return: (Response specifics, status code)
    """
    logging.info("Starting confirm forgot password flow.")
    email, password, confirmation_code = verify_parameters(
        body, "email", "password", "confirmationCode"
    )

    client: CognitoClient = boto3.client("cognito-idp")
    try:
        client.confirm_forgot_password(
            ClientId=CLIENT_ID,
            Username=email,
            ConfirmationCode=confirmation_code,
            Password=password,
        )
    except ParamValidationError as e:
        logging.exception("")
        report = e.kwargs["report"]
        if "Invalid type for parameter ConfirmationCode" in report:
            return ResponseData(message="Invalid confirmation code.", exception=True), 400
        elif "Invalid length for parameter Password" in report:
            return ResponseData(message="Invalid password.", exception=True), 400
        else:
            return ResponseData(message="Unexpected exception encountered.", exception=True), 500
    except client.exceptions.UserNotFoundException:
        logging.exception("")
        return ResponseData(message="This email is not registered.", exception=True), 404
    except client.exceptions.InvalidPasswordException:
        logging.exception("")
        return ResponseData(message="Invalid password.", exception=True), 400
    except client.exceptions.CodeMismatchException:
        logging.exception("")
        return ResponseData(message="Invalid confirmation code.", exception=True), 400
    except client.exceptions.NotAuthorizedException:
        logging.exception("")
        return (
            ResponseData(message="Password reset has already been confirmed.", exception=True),
            400,
        )
    except Exception:
        logging.exception("")
        return ResponseData(message="Unexpected exception encountered.", exception=True), 500

    logging.info("Confirm forgot password flow successful.")
    return ResponseData(message="Your password has been successfully reset!"), 200
