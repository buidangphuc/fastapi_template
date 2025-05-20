if ! command -v poetry &> /dev/null
then
    echo "Poetry could not be found. Please install Poetry first."
    exit
fi

# Initialize poetry project
poetry init --no-interaction --name "my_project" --dependency "python" --dev-dependency "pytest" --dev-dependency "pytest-dotenv"

# Check if requirements.txt exists
if [ ! -f requirements.txt ]; then
    echo "requirements.txt not found!"
    exit 1
fi

# Add all dependencies from requirements.txt
echo "Adding dependencies from requirements.txt"
poetry add $(cat requirements.txt)

# Install the dependencies without installing the project itself
echo "Installing dependencies (without root package)"
poetry install --no-root

echo "Poetry project setup completed."
