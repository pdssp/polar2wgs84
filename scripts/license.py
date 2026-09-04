# subprocess: trusted internal tooling, no user input
import subprocess  # nosec B404

import toml

# Ouverture du fichier pyproject.toml
with open("pyproject.toml") as file:
    # Parsing du fichier TOML
    pyproject = toml.loads(file.read())

# Récupération des dépendances de développement
dev_dependencies = pyproject["project"]["dependencies"]

# Boucle pour extraire les noms des packages sans la version
packages = []
for package in dev_dependencies:
    package_name = package.split("==")[0].strip()
    packages.append(package_name)

# subprocess.run: fixed argv, no shell, no untrusted input
subprocess.run(  # nosec B603
    [
        "pip-licenses",
        "--from",
        "meta",
        "-f",
        "md",
        "-a",
        "-u",
        "-d",
        "--output-file",
        "docs/legal.md",
        "-p",
    ]
    + packages
)
