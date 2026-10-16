# AI Food Calorie Estimator

Platewise is a local Flask web app for estimating the calories and macronutrients in a meal photo. It combines a real, pretrained Food-101 image classifier with a small, source-documented nutrition catalog and an SQLite meal diary. Every displayed nutrition value is an estimate.

## Technologies

- **Frontend:** HTML templates, CSS, and browser-side JavaScript
- **Backend:** Python and Flask
- **Image recognition:** Hugging Face Transformers with the pretrained `nateraw/food` Food-101 Vision Transformer
- **Nutrition and meal storage:** SQLite, populated from the bundled food catalog
- **Charts:** Chart.js (loaded from its public CDN)
- **Image handling:** Pillow

## Features

- Upload or drag in a JPEG, PNG, or WebP food photo (up to 8 MB) and preview it before analysis.
- Classify a photo with the pretrained [`nateraw/food`](https://huggingface.co/nateraw/food) Vision Transformer, fine-tuned on Food-101. The model is loaded on CPU on first use; its model files are cached by Hugging Face.
- Display an explicit manual-selection prompt rather than inventing a result when the model is unavailable, its confidence is low, or its label has no matching nutrition entry.
- Choose from 20 Indian dishes, including idli, dosa, chapati, rice, vegetable/chicken biryani, dal, paneer curry, and others. These are manual options: the Food-101 model does not include these Indian dish labels.
- Adjust serving weight in grams and record a meal type. Estimated calories, protein, carbohydrates, and fat scale from the selected portion.
- See today's estimated totals, a Chart.js seven-day calorie chart, and a date-filterable meal history. Meals and catalog entries are stored locally in SQLite.
- Retain meal photos in the local `instance/uploads` directory so they can appear in the diary.

## Requirements

- Windows 10/11
- Python 3.10 or newer (64-bit recommended)
- Internet access on first AI inference to download the model and its files
- Several GB of free disk space for PyTorch and the cached model

The first image inference can take longer while the model downloads. Subsequent inferences use the local model cache. The app works without model dependencies for manually selected meals; without a network connection and a populated model cache, AI recognition will report an error and offer manual selection.

## Install and run in VS Code

Open this project folder in VS Code. In the integrated PowerShell terminal, run:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

If PowerShell blocks local virtual-environment activation, run this in the current terminal first:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Alternatively, skip activation and run the environment's executable directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open **http://127.0.0.1:5000**. Stop the development server with **Ctrl+C**.

To run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Nutrition data and limitations

The bundled SQLite food catalog stores a reference per-100-gram estimate and a source note for every entry. Basic ingredient values and representative Indian recipes are based on the [Indian Food Composition Tables 2017 (ICMR–NIN)](https://www.nin.res.in/downloads/IFCT2017.pdf); general foods are based on representative entries in [USDA FoodData Central](https://fdc.nal.usda.gov/). Composite dish recipes, ingredients, oil, brands, and cooking methods vary; a catalog value is not a laboratory measurement of the uploaded serving. Portion weights are supplied or adjusted by the user.

Food-101 contains 101 food classes, not every cuisine or dish. The current nutrition-matched image labels cover a subset of common classes. A model confidence score is not a guarantee of correctness. Unsupported or uncertain predictions are not converted into nutrition estimates; choose a food manually instead. This app does not provide medical or dietary advice.

Chart.js and web fonts load from their public CDNs. If those services are unavailable, the core Flask app and meal diary still work, although the chart or custom fonts may not load.

## Project layout

```text
app.py                    Flask development entry point
food_estimator/
  __init__.py             App factory and application configuration
  database.py             SQLite schema, catalog, and diary queries
  nutrition.py            Per-100-g catalog and Food-101 label mapping
  recognition.py          Pretrained image-classifier integration
  routes.py               Upload, estimate, save, history, and image routes
templates/                Responsive dashboard, history, and error pages
static/                   CSS and browser-side preview/chart behavior
tests/                    Flask route and diary tests
requirements.txt          Python dependencies
```

## Configuration and privacy

The app requires no API key. The pretrained model is fetched from Hugging Face and cached in the current user's normal Hugging Face cache. The SQLite database and uploaded images are local under `instance/` by default; that directory is ignored by Git. Do not expose Flask's development server to an untrusted network. For deployment, use a production WSGI server, HTTPS, suitable upload/storage protections, and a configured secret/session policy if authentication or sessions are added.

The repository `.gitignore` excludes local virtual environments, Python caches, `instance/` (including the database and uploaded photos), `.env` configuration files, and local model caches/weights. Keep credentials and personal data out of tracked source files. Before publishing, review the files staged in Git; ignore rules do not remove files that were already committed or explicitly force-added.
