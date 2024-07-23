try:
    from weasyprint import HTML
    print("WeasyPrint is installed correctly.")
except ModuleNotFoundError as e:
    print(f"Error: {e}")
