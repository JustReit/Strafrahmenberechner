from flask import Flask, render_template, request, jsonify
import re
import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, String, Integer, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

import definitions
from definitions import unit_factors, number_words, laws

app = Flask(__name__)
Base = declarative_base()


class Law(Base):
    __tablename__ = 'laws'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    paragraphs = relationship('Paragraph', back_populates='law')


class Paragraph(Base):
    __tablename__ = 'paragraphs'
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    absatz = Column(String, nullable=False)
    min_value = Column(Integer, nullable=False)
    max_value = Column(Integer, nullable=False)
    fine = Column(String, nullable=True)
    lawtext = Column(Text, nullable=False)
    bezeichnung = Column(String, nullable=False)
    law_id = Column(Integer, ForeignKey('laws.id'), nullable=False)
    law = relationship('Law', back_populates='paragraphs')


# Create an engine and a session
engine = create_engine('sqlite:///laws.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()


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

        # Check if the law already exists in the database
        law_entry = session.query(Law).filter_by(url=url).first()

        if law_entry:
            # Law exists, retrieve paragraphs from the database
            for paragraph in law_entry.paragraphs:
                data.append({
                    'name': law_entry.name, 'url': law_entry.url, 'title': paragraph.title,
                    'absatz': paragraph.absatz, 'minValue': paragraph.min_value,
                    'maxValue': paragraph.max_value, 'fine': paragraph.fine, 'lawtext': paragraph.lawtext,
                    'bezeichnung': paragraph.bezeichnung
                })
        else:
            # Fetch data from the URL
            response = requests.get(url)
            html = response.text
            soup = BeautifulSoup(html, 'lxml')
            paragraphs = [p for p in soup.find_all('div', class_='jurAbsatz') if
                          "Freiheitsstrafe" in p.text and any(word in p.text for word in definitions.penality_words)]
            law_entry = Law(name=name, url=url)
            session.add(law_entry)
            session.commit()

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
                    # Save each paragraph to the database
                    new_paragraph = Paragraph(
                        title=title.text, absatz=absatz, min_value=min_value,
                        max_value=max_value, fine=fine, lawtext=paragraph.text,
                        bezeichnung=bezeichnung.text, law_id=law_entry.id
                    )
                    session.add(new_paragraph)
                    session.commit()

                    # Append to response data
                    data.append({
                        'name': name, 'url': url, 'title': title.text,
                        'absatz': absatz, 'minValue': min_value,
                        'maxValue': max_value, 'fine': fine, 'lawtext': paragraph.text,
                        'bezeichnung': bezeichnung.text
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
            unit_factor = unit_factors[match.group(2)]
            min_val = 1 / 12
            fine = False
            if is_fine:
                fine = True

            if is_life_sentence:
                max_val = "Lebenslänglich"

            return min_val, max_val * unit_factor, fine
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
