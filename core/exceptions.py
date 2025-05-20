class LoadEnvException(Exception):
    def __str__(self) -> str:
        return "Required variables undefined, please check your .env file."
