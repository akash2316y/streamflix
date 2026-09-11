
class InvalidHash(Exception):
    message = "Invalid hash"

class FIleNotFound(Exception):
    message = "File not found"

class LinkUnavailable(Exception):
    message = "This link has expired or has been removed by the admin."