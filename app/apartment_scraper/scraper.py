import requests
from bs4 import BeautifulSoup

def scrape_apartment(url):
    response = requests.get(url)
    response.raise_for_status()  # Raises an error for bad responses

    soup = BeautifulSoup(response.text, 'html.parser')

    def safe_get_text(selector):
        element = soup.select_one(selector)
        return element.get_text(strip=True) if element else "N/A"

    def get_value_for_label(label):
        label_cell = soup.find(text=label)
        if label_cell:
            return label_cell.find_parent('td').find_next_sibling('td').get_text(strip=True)
        return "N/A"

    details = {
        "title": safe_get_text("h1"),
        "address": safe_get_text("h2"),
        "gross_rent": get_value_for_label("Gross rent (incl. utilities):"),
        "net_rent": get_value_for_label("Net rent (excl. utilities):"),
        "utilities": get_value_for_label("Utilities:"),
        "reference": get_value_for_label("Reference:"),
        "number_of_rooms": get_value_for_label("Number of rooms:"),
        "floor": get_value_for_label("Floor:"),
        "living_space": get_value_for_label("Livingspace:"),
        "year_of_construction": get_value_for_label("Year of construction:"),
        "facilities": get_value_for_label("Facilities:"),
        "availability": get_value_for_label("Available:"),
    }

    # Extract the Markdown description
    markdown_description = soup.select_one("div.markdown")  # Target the correct div
    if markdown_description:
        # Joining all paragraphs together to form a complete description
        paragraphs = markdown_description.find_all('p')
        details["description"] = "\n\n".join(p.get_text(strip=True) for p in paragraphs)
    else:
        details["description"] = "N/A"

    return details
