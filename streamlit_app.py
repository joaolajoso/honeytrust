import streamlit as st
from streamlit_tags import st_tags_sidebar
import pandas as pd
from pandas import json_normalize
import json
import requests
from datetime import datetime
from scraper import (fetch_html_selenium, save_raw_data, format_data,
                     save_formatted_data, calculate_price, html_to_markdown_with_readability,
                     create_dynamic_listing_model, create_listings_container_model)

from assets import PRICING, METHOD
import re




# Initialize Streamlit app
st.set_page_config(page_title="Universal Web Scraper")
st.title("Universal Web Scraper 🦑")

# Sidebar components
st.sidebar.title("Web Scraper Settings")
method_selection = st.sidebar.selectbox("Select Method Scrapper LINK/POST/CHAT", options=list(METHOD.keys()), index=0)
model_selection = st.sidebar.selectbox("Select Model", options=list(PRICING.keys()), index=0)
url_input = st.sidebar.text_input("Enter URL")

# Tags input specifically in the sidebar
tags = st.sidebar.empty()  # Create an empty placeholder in the sidebar
tags = st_tags_sidebar(
    label='Enter Fields to Extract:',
    text='Press enter to add a tag',
    value=[],  # Default values if any
    suggestions=[],  # You can still offer suggestions, or keep it empty for complete freedom
    maxtags=-1,  # Set to -1 for unlimited tags
    key='tags_input'
)
# Sidebar input for payload and headers when POST is selected
if method_selection == 'POST':
    payload_input = st.sidebar.text_area("Enter payload (JSON format)")
    headers_input = st.sidebar.text_area("Enter headers (JSON format)")

    # Convert payload and headers from string to dictionary
    try:
        payload = json.loads(payload_input) if payload_input else {}
    except json.JSONDecodeError:
        st.error("Invalid JSON in payload input")
        payload = {}

    try:
        headers = json.loads(headers_input) if headers_input else {}
    except json.JSONDecodeError:
        st.error("Invalid JSON in headers input")
        headers = {}
    

st.sidebar.markdown("---")

# Process tags into a list
fields = tags

# Initialize variables to store token and cost information
input_tokens = output_tokens = total_cost = 0  # Default values

def json_to_markdown_table(json_data):
    if not json_data:
        return "No data available"

    if isinstance(json_data, dict):
        # Handle if json_data is a dictionary (e.g., nested structure)
        json_data = [json_data]

    # Assuming json_data is a list of dictionaries
    columns = json_data[0].keys()

    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = []
    for item in json_data:
        row = "| " + " | ".join(str(item.get(col, "")) for col in columns) + " |"
        rows.append(row)

    return "\n".join([header, separator] + rows)

# Buttons to trigger scraping
def perform_scrape():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if method_selection == 'LINK':
        try:
            raw_html = fetch_html_selenium(url_input)
            st.markdown(raw_html, unsafe_allow_html=True)
            markdown = html_to_markdown_with_readability(raw_html)
            save_raw_data(markdown, timestamp)

          
        except Exception as e:
            st.error(f"An error occurred: {e}")
            return None, None, None, 0, 0, 0, ""

    elif method_selection == 'POST':
        response = requests.post(url_input, json=payload, headers=headers, stream=True)
        #st.write(response.text)  # Print the full raw response for debugging
        #st.write(f"Content-Type: {response.headers.get('Content-Type')}")

        if response.status_code == 200:
            # Check if the response has valid JSON content
            if response.content:
                try:
                    #response_content = response.content.decode('utf-8')
                    # Accumulate response content from chunks
                    response_content = ""
                    for chunk in response.iter_content(chunk_size=1024):  # Adjust chunk size if needed
                        response_content += chunk.decode('utf-8')
                    # Remove trailing commas before closing braces
                    cleaned_response = re.sub(r',\s*([}\]])', r'\1', response_content)
 
                    
                    try:
                        data = response.json().get('items', [])
                        #data = json.loads(cleaned_response)
                        #st.write("Cleaned JSON is valid")
                    except json.JSONDecodeError as e:
                        st.error(f"Still unable to decode JSON: {e}")
                      
                    # Save response to a file for further inspection
                    st.download_button("Download JSON source", data=data, file_name=f"{timestamp}_data.json")


                    df = json_normalize(data)
                    #df = pd.DataFrame(data)
                    st.write("Scraped Data:", df)
                    st.write(f"Total response length: {len(response_content)}")
                    #print(response_content[:1000])  # Log the first 1000 characters for debugging
                    #print("Ok json!")
                    #data = json.loads(response_content)
                    #st.write("Scraped Data Source:", data)
                    markdown = json_to_markdown_table(data)
                    save_raw_data(markdown, timestamp)
                except json.JSONDecodeError:
                    st.error("Invalid JSON response. Check the API or payload.")
                    return None, None, None, 0, 0, 0, ""
            else:
                st.error("Empty response received.")
                return None, None, None, 0, 0, 0, ""
        else:
            st.error(f"Error: {response.status_code}")
            return None, None, None, 0, 0, 0, ""

    else:
            markdown = f"Grab all data from {url_input}"
          
          
    DynamicListingModel = create_dynamic_listing_model(fields)
    DynamicListingsContainer = create_listings_container_model(DynamicListingModel)
    formatted_data, tokens_count = format_data(markdown, DynamicListingsContainer, DynamicListingModel, model_selection)
    input_tokens, output_tokens, total_cost = calculate_price(tokens_count, model=model_selection)
    df = save_formatted_data(formatted_data, timestamp)
    
    return df, formatted_data, markdown, input_tokens, output_tokens, total_cost, timestamp

if 'perform_scrape' not in st.session_state:
    st.session_state['perform_scrape'] = False

if st.sidebar.button("Scrape"):
    with st.spinner('Please wait... Data is being scraped.'):
        st.session_state['results'] = perform_scrape()
        st.session_state['perform_scrape'] = True



if st.session_state.get('perform_scrape'):
    if 'results' not in st.session_state:
        st.session_state['results'] = None
    else:
        df, formatted_data, markdown, input_tokens, output_tokens, total_cost, timestamp = st.session_state['results']

        # Display the DataFrame and other data
        st.write("Scraped Data:", df)
        st.sidebar.markdown("## Token Usage")
        st.sidebar.markdown(f"**Input Tokens:** {input_tokens}")
        st.sidebar.markdown(f"**Output Tokens:** {output_tokens}")
        st.sidebar.markdown(f"**Total Cost:** :green-background[***${total_cost:.4f}***]")

        # Create columns for download buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button("Download JSON", data=json.dumps(formatted_data, indent=4), file_name=f"{timestamp}_data.json")
        with col2:
            if isinstance(formatted_data, str):
                data_dict = json.loads(formatted_data)
            else:
                data_dict = formatted_data

            first_key = next(iter(data_dict))
            main_data = data_dict[first_key]
            df = pd.DataFrame(main_data)
            st.download_button("Download CSV", data=df.to_csv(index=False), file_name=f"{timestamp}_data.csv")
        with col3:
            st.download_button("Download Markdown", data=markdown, file_name=f"{timestamp}_data.md")

# Ensure that these UI components are persistent and don't rely on re-running the scrape function
if 'results' in st.session_state:
    df, formatted_data, markdown, input_tokens, output_tokens, total_cost, timestamp = st.session_state['results']
