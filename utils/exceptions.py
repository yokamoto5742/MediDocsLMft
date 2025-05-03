class AppError(Exception):
    pass

class AuthError(AppError):
    pass

class APIError(AppError):
    pass

class DatabaseError(AppError):
    pass
