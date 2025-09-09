from flask import jsonify

def error_response(error: str, message: str, status: int):
    return jsonify({"error": error, "message": message}), status