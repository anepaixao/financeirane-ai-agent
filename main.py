from financeirane import main as package_main
from financeirane.main import criar_bot, registrar_handlers

__all__ = ["criar_bot", "main", "registrar_handlers"]


def main():
    package_main.main()


if __name__ == "__main__":
    main()
