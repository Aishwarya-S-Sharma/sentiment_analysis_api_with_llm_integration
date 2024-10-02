from flask import Flask, request, render_template, flash, send_file, redirect, url_for, session
from groq import Groq
import json
import re
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = 'sentiment_analysis'  # Necessary for flash messages

# Initialize Groq API client
API_KEY = "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"  # Replace with your actual API key
client = Groq(api_key=API_KEY)

# Sentiment Analysis Function
def analyze_sentiment(text):
    try:
        chat_completion = client.chat.completions.create(
            messages=[{
                "role": "system",
                "content": "You are a helpful assistant that performs sentiment analysis."
            }, {
                "role": "user",
                "content": f"Analyze the sentiment of the following text: '{text}' and return a JSON object with positive, negative, and neutral scores."
            }],
            model="llama3-8b-8192",
            temperature=0.5,
            max_tokens=1024,
            top_p=1,
            stop=None,
            stream=False,
        )

        sentiment_result = chat_completion.choices[0].message.content

        # Extract and return the structured JSON response
        match = re.search(r'({.*?})', sentiment_result, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return {"error": "Failed to parse the sentiment analysis result."}

        return {"error": "No valid JSON found in the response."}

    except Exception as e:
        return {"error": str(e)}

def classify_sentiment(scores):
    """Classify the sentiment based on the scores."""
    if 'error' in scores:
        return 'Error'
    
    if scores['positive'] > scores['negative']:
        return 'Positive'
    elif scores['negative'] > scores['positive']:
        return 'Negative'
    else:
        return 'Neutral'

@app.route('/', methods=['GET', 'POST'])
def index():
    sentiment_result = None
    sentiment_classification = None
    batch_results = None
    output_file_path = None
    review_entered = None  # Variable to hold the individual review entered

    # Process POST requests
    if request.method == 'POST':
        # Individual text analysis
        if 'content' in request.form:
            text = request.form['content'].strip()  # Trim whitespace

            if not text:  # Check if the text input is empty
                flash('Please enter text to analyze.')  # Flash message for empty input
                return redirect(url_for('index'))  # Redirect to the main page

            # Analyze the text input
            sentiment_result = analyze_sentiment(text)
            sentiment_classification = classify_sentiment(sentiment_result)
            review_entered = text  # Store the entered review

        # Batch file analysis
        elif 'file' in request.files:
            uploaded_file = request.files['file']

            if uploaded_file:
                try:
                    # Check the file extension
                    if uploaded_file.filename.endswith('.csv'):
                        df = pd.read_csv(uploaded_file)
                    elif uploaded_file.filename.endswith('.xlsx'):
                        df = pd.read_excel(uploaded_file)
                    else:
                        flash('Unsupported file format. Please upload a CSV or XLSX file.')
                        return redirect(url_for('index'))  # Redirect to main page

                    # Ensure there is a column named "Review"
                    if 'Review' not in df.columns:
                        flash('The uploaded file must contain a "Review" column.')
                        return redirect(url_for('index'))  # Redirect to main page

                    # Extract reviews and limit to 50 reviews
                    reviews = df['Review'].head(50)
                    batch_results = []

                    # Analyze each review
                    for review in reviews:
                        print(f"processing review : {review}")
                        sentiment_result = analyze_sentiment(review)
                        sentiment_classification = classify_sentiment(sentiment_result)

                        # Store the results in the list
                        batch_results.append({
                            "review": review,
                            "result": sentiment_result,
                            "classification": sentiment_classification
                        })

                    # Create DataFrame for results
                    results_df = pd.DataFrame(batch_results)

                    # Export to CSV
                    output_file_path = 'sentiment_analysis_results.csv'
                    results_df.to_csv(output_file_path, index=False)

                    # Display success message
                    flash('Sentiment analysis completed for the batch. You can download the results now.')

                except Exception as e:
                    flash(f'Error processing file: {str(e)}')
                    return redirect(url_for('index'))  # Redirect to main page

    return render_template('index.html', sentiment_result=sentiment_result, 
                           sentiment_classification=sentiment_classification,
                           batch_results=batch_results, 
                           output_file=output_file_path, 
                           review_entered=review_entered)

@app.route('/download')
def download_file():
    """Download the exported results file."""
    file_path = 'sentiment_analysis_results.csv'
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return "File not found.", 404

if __name__ == "__main__":
    app.run(debug=True)
