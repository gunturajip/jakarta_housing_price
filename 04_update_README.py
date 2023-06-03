from datetime import datetime, timedelta

with open("README.md", "w", encoding="utf-8") as file:
    file.write(str(datetime.now() + + timedelta(hours=7)))