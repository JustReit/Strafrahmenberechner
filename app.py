from flask import Flask, render_template, request, jsonify
import re
import requests
import requests_cache
from bs4 import BeautifulSoup

from definitions import unit_factors, number_words, laws

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/data')
def laws_data():
    data = []
    for law in laws:
        data.append(law)

    return jsonify(data), 200


@app.route('/api/paragraphen', methods=['POST'])
def paragraphen_data():
    laws = request.get_json()
    data = []

    for url_data in laws:
        url = url_data.get('url')
        name = url_data.get('value')
        requests_cache.install_cache("Gesetze_Cache")
        response = requests.get(url)
        html = response.text
        soup = BeautifulSoup(html, 'lxml')
        paragraphs = [p for p in soup.find_all('div', class_='jurAbsatz') if "Freiheitsstrafe" in p.text and "bestraft" in p.text]

        for paragraph in paragraphs:
            title = paragraph.parent.parent.parent.parent.find('span', class_='jnenbez')
            bezeichnung = paragraph.parent.parent.parent.parent.find('span', class_='jnentitel')

            absatz = extract_absatz(paragraph.text)

            try:
                min_value, max_value, fine = text_to_min_max(paragraph.text)
            except Exception as e:
                print("Error:", e)
                continue

            if title and min_value != 0 and max_value != 0:
                data.append({
                    'name': name, 'url': url, 'title': title.text,
                    'absatz': absatz, 'minValue': min_value,
                    'maxValue': max_value, 'fine': fine, 'lawtext': paragraph.text, 'bezeichnung': bezeichnung.text
                })

    return jsonify(data), 200


def text_to_min_max(sentence, fine=False):
    def extract_values(match, is_fine=False):
        if match.group(3) in number_words and match.group(4) in unit_factors and match.group(
                1) in number_words and match.group(2) in unit_factors:
            min_val = number_words[match.group(1)]
            unit_factor_min = unit_factors[match.group(2)]
            max_val = number_words[match.group(3)]
            unit_factor_max = unit_factors[match.group(4)]
            fine = False
            if is_fine:
                fine = True

            return min_val * unit_factor_min, max_val * unit_factor_max, fine
        return 0, 0, False

    def extract_max_value(match, is_fine=False, is_life_sentence=False):
        if match.group(1) in number_words:
            max_val = number_words[match.group(1)]
            min_val = 1 / 12
            fine = False
            if is_fine:
                fine = True

            if is_life_sentence:
                max_val = "Lebenslänglich"

            return min_val, max_val, fine
        return 0, 0, False

    def extract_not_under(match, is_fine=False, is_life_sentence=False):
        if match.group(1) in number_words and match.group(2) in unit_factors:

            min_val = number_words[match.group(1)]
            unit_factor = unit_factors[match.group(2)]
            max_val = 15
            fine = False
            if is_fine:
                fine = True

            if is_life_sentence:
                max_val = "Lebenslänglich"

            return min_val * unit_factor, max_val, fine
        return 0, 0, False

    min_value, max_value = 0, 0
    match = re.search(r"von (\w+) (\w+) bis zu (\w+) (\w+)", sentence)

    if match:
        return extract_values(match, "Geldstrafe" in sentence)

    match = re.search(r"bis zu (\w+) (\w+)", sentence)
    if match:
        return extract_max_value(match, "Geldstrafe" in sentence,
                                 "lebenslange Freiheitsstrafe" in sentence or "lebenslanger Freiheitsstrafe" in sentence)

    match = re.search(r"bis (\w+) (\w+)", sentence)
    if match:
        return extract_max_value(match, "Geldstrafe" in sentence,
                                 "lebenslange Freiheitsstrafe" in sentence or "lebenslanger Freiheitsstrafe" in sentence)
    match = re.search(r"mit lebenslanger Freiheitsstrafe (\w+)", sentence)
    if match and match.group(1) == "bestraft":
        return 15, "Lebenslänglich", False

    match = re.search(r"nicht unter (\w+) (\w+)", sentence)
    if match:
        return extract_not_under(match, "Geldstrafe" in sentence,
                                 "lebenslange Freiheitsstrafe" in sentence or "lebenslanger Freiheitsstrafe" in sentence)

    return min_value, max_value, fine


def extract_numbers_p(text):
    # RegEx zum Extrahieren von Zahlen
    regex = r"\d+"
    num_p = text.split()

    # Iteriere über num_p und führe für jedes Element findall() aus
    numbers_p = []
    for word in num_p:
        numbers_p += re.findall(regex, word)

    # Konvertiere die gefundenen Zeichenfolgen in Zahlen
    numbers_p = [int(x) for x in numbers_p]
    return numbers_p


def extract_absatz(text):
    regex = r"\(\d+\)"
    num_a = text.split()

    # Iteriere über num_a und führe für jedes Element findall() aus
    numbers_a = []
    for word in num_a:
        numbers_a += re.findall(regex, word)

    # Konvertiere die gefundenen Zeichenfolgen in Zahlen
    numbers_a = [x.strip("()") for x in numbers_a]
    numbers_a = [int(x) for x in numbers_a]

    if numbers_a:
        return numbers_a[0]
    else:
        return 1


if __name__ == '__main__':
    app.run(host="0.0.0.0")
