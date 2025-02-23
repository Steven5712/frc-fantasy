# Use official Python 3.9 image as the base
FROM python:3.9-slim

# Set working directory inside the container
WORKDIR /app

# Copy your project files into the container
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Tell Docker which port your app uses (Flask defaults to 5000)
EXPOSE 5000

# Command to run your app
CMD ["python", "app.py"]