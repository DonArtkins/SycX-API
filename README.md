# SycX-API 🚀

A minimalist, high-performance Flask REST API template with built-in rate limiting and best practices. This is a great starting point for building robust APIs.

## Features

- 🚄 High-performance REST API setup
- 🔒 Built-in rate limiting (configurable)
- 🌐 CORS enabled (for cross-origin requests)
- 📝 Clear project structure
- 🔄 Version control ready (Git pre-initialized)
- 📦 Minimal dependencies
- 🤖 ML model integration ready

## Quick Start

1. **Enter Project Directory:**

    ```bash
    cd SycX-API
    ```

2. **Activate the Virtual Environment:**

    ```bash
    # Linux/Mac
    source venv/bin/activate
    ```

    ```bash
    # Windows
    .\venv\Scripts\activate
    ```

3. **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Run the API:**

    ```bash
    python3 run.py
    ```

    The API will start in debug mode. You'll see output in your terminal.

## API Structure

The project follows a clear structure:

```
SycX-API/
├── app/
│   ├── api/
│   │   └── v1/              # API version 1
│   │       ├── __init__.py  # Initializes the v1 API
│   │       └── routes.py    # Defines API endpoints
│   ├── config/
│   │   └── config.py        # Configuration settings
│   ├── models/             # Store your ML models here
│   │   ├── __init__.py
│   │   └── trained_models/ # Directory for saved models
│   ├── services/          # Business logic and model inference
│   │   └── __init__.py
│   ├── utils/
│   │   └── helpers.py      # Utility functions (e.g., rate limiting)
│   └── __init__.py         # Initializes the app package
├── tests/                # Add your unit tests here
├── docs/                 # API documentation
├── venv/                 # Virtual environment
├── .env                  # Environment variables
├── .gitignore           # Git ignore rules
├── LICENSE              # License information
├── CONTRIBUTING.md      # Contribution guidelines
├── README.md            # This file!
├── requirements.txt     # Python package dependencies
└── run.py              # Main application entry point
```

## Using the API

### Making Requests with Postman

1. **Install Postman:**
   Download and install from [postman.com](https://www.postman.com/downloads/)

2. **Basic Endpoints:**
   - Health Check:
     - Method: GET
     - URL: `http://localhost:5000/api/v1/health`
   
   - Hello World:
     - Method: GET
     - URL: `http://localhost:5000/api/v1/hello`
     
   - Hello World (POST):
     - Method: POST
     - URL: `http://localhost:5000/api/v1/hello`
     - Headers: `Content-Type: application/json`
     - Body:
       ```json
       {
           "message": "Hello from Postman!"
       }
       ```

### Adding Custom Endpoints

1. **Create a New Route:**
   In `app/api/v1/routes.py`, add your new endpoint:

   ```python
   class MyNewEndpoint(Resource):
       @rate_limit
       def get(self):
           return {"message": "My new endpoint"}, 200
       
       @rate_limit
       def post(self):
           data = request.get_json()
           # Process your data here
           return {"result": "Processing complete"}, 201

   # Register your new endpoint
   api.add_resource(MyNewEndpoint, '/my-endpoint')
   ```

2. **Test Your Endpoint:**
   - URL: `http://localhost:5000/api/v1/my-endpoint`
   - Methods: GET, POST
   - Headers: `Content-Type: application/json`

### Integrating ML Models

1. **Project Structure for ML:**
   - Place model classes in `app/models/`
   - Store trained models in `app/models/trained_models/`
   - Put inference logic in `app/services/`

2. **Example Model Integration:**

   ```python
   # app/models/custom_model.py
   from transformers import Pipeline  # or your preferred ML library

   class MyModel:
       def __init__(self):
           self.model = None
           
       def load_model(self, model_path):
           # Load your model here
           self.model = Pipeline.from_pretrained(model_path)
           
       def predict(self, input_data):
           # Make predictions
           return self.model(input_data)
   ```

3. **Create a Service:**

   ```python
   # app/services/model_service.py
   from app.models.custom_model import MyModel
   
   class ModelService:
       def __init__(self):
           self.model = MyModel()
           self.model.load_model('app/models/trained_models/my_model')
           
       def get_prediction(self, input_data):
           return self.model.predict(input_data)
   ```

4. **Create an Endpoint:**

   ```python
   # app/api/v1/routes.py
   from app.services.model_service import ModelService
   
   class PredictionEndpoint(Resource):
       def __init__(self):
           self.model_service = ModelService()
   
       @rate_limit
       def post(self):
           data = request.get_json()
           prediction = self.model_service.get_prediction(data['input'])
           return {'prediction': prediction}, 200
   
   # Register endpoint
   api.add_resource(PredictionEndpoint, '/predict')
   ```

5. **Make Prediction Request:**
   - Method: POST
   - URL: `http://localhost:5000/api/v1/predict`
   - Headers: `Content-Type: application/json`
   - Body:
     ```json
     {
         "input": "your input data here"
     }
     ```

### Training Models

1. **Create Training Script:**
   Place your training scripts in `app/models/training/`:

   ```python
   # app/models/training/train_model.py
   def train_model(data_path, save_path):
       # Load your data
       # Train your model
       # Save the model
       model.save(save_path)
   
   if __name__ == '__main__':
       train_model('path/to/data', 'app/models/trained_models/my_model')
   ```

2. **Run Training:**
   ```bash
   python -m app.models.training.train_model
   ```

## Best Practices

1. **API Versioning:**
   - Keep different versions in separate directories (`app/api/v1/`, `app/api/v2/`)
   - Use version prefix in URLs (`/api/v1/`, `/api/v2/`)

2. **Rate Limiting:**
   - Configure in `.env`:
     ```
     RATE_LIMIT=1000
     RATE_LIMIT_PERIOD=15
     ```

3. **Error Handling:**
   - Use appropriate HTTP status codes
   - Return descriptive error messages
   - Log errors properly

4. **Model Management:**
   - Version your models
   - Keep model weights in `app/models/trained_models/`
   - Use environment variables for model paths
   - Document model requirements and dependencies

5. **Testing:**
   - Write unit tests in `tests/`
   - Test API endpoints
   - Test model inference
   - Run tests before deployment

## Security Best Practices

1. **API Security:**
   - Use HTTPS in production
   - Implement authentication if needed
   - Validate all input data
   - Set appropriate CORS policies

2. **Model Security:**
   - Validate model inputs
   - Set resource limits
   - Monitor model performance
   - Regular security updates

## Contributing

See `CONTRIBUTING.md` for details on how to contribute to this project.

## License

MIT License. See `LICENSE` for more information.
