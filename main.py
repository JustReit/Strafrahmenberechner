import re
import requests
import requests_cache
from bs4 import BeautifulSoup

from definitions import help_words, unit_factors, number_words, laws, gesetz_bezeichnung


def text_to_min_max(sentence, fine=False):
  min_value = 0
  max_value = 0

  # Erste Bedingung: von {min} {unit_factors} bis zu {max} {unit_factors}
  match = re.search(r"von (\w+) (\w+) bis zu (\w+) (\w+)", sentence)
  if match and match.group(2) in unit_factors:
    min_value = number_words[match.group(1)]
    unit_factor_min = unit_factors[match.group(2)]
    max_value = number_words[match.group(3)]
    unit_factor_max = unit_factors[match.group(4)]

    if "Geldstrafe" in sentence:
      fine = True
    if "lebenslange Freiheitsstrafe" in sentence or "lebenslanger Freiheitsstrafe" in sentence:
      max_value = "Lebenslänglich"
      unit_factor_max = None
    return (min_value * unit_factor_min, max_value * unit_factor_max, fine)

  # Zweite Bedingung: bis zu {max} {unit_factors} ; max muss das einzige number_word im gesamten text sein damit die bedingung eintritt. Min ist in diesem Fall 1/12
  match = re.search(r"bis zu (\w+) (\w+)", sentence)
  if match and match.group(2) in unit_factors:
    max_value = number_words[match.group(1)]
    unit_factor = unit_factors[match.group(2)]
    min_value = 1 / 12

    if "Geldstrafe" in sentence:
      fine = True
    if "lebenslange Freiheitsstrafe" in sentence or "lebenslanger Freiheitsstrafe" in sentence:
      max_value = "Lebenslänglich"
    return (min_value, max_value * unit_factor, fine)

  match = re.search(r"bis (\w+) (\w+)", sentence)
  if match and "Freiheitsstrafe" in sentence and match.group(2) in unit_factors:
    max_value = number_words[match.group(1)]
    unit_factor = unit_factors[match.group(2)]
    min_value = 1 / 12

    if "Geldstrafe" in sentence:
      fine = True
    if "lebenslange Freiheitsstrafe" in sentence or "lebenslanger Freiheitsstrafe" in sentence:
      max_value = "Lebenslänglich"
    return (min_value, max_value * unit_factor, fine)

  # Dritte Bedingung: nicht unter {min} {unit_factors}; Hier muss min ebenfalls die einzige Zahl sein. Ist die s erfüllt ist max gleich 15
  match = re.search(r"nicht unter (\w+) (\w+)", sentence)
  if match and match.group(2) in unit_factors:
    min_value = number_words[match.group(1)]
    unit_factor = unit_factors[match.group(2)]
    max_value = 15

    if "Geldstrafe" in sentence:
      fine = True
    if "lebenslange Freiheitsstrafe" in sentence or "lebenslanger Freiheitsstrafe" in sentence:
      max_value = "Lebenslänglich"
    return (min_value * unit_factor, max_value, fine)

  if "lebenslange Freiheitsstrafe" in sentence or "lebenslanger Freiheitsstrafe" in sentence:
    min_value = 15
    max_value = "Lebenslänglich"
    if "Geldstrafe" in sentence:
      fine = True

    return (min_value, max_value, fine)

  return (min_value, max_value, fine)


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


def reduce_sentence(min, max):
  for _ in range(num_reductions):
    if max == "Lebenslänglich":
      max = 15
      min = 3
    else:
      max = max * 0.75
    if min == 10 or min == 5:
      min = 2
    elif min == 3 or min == 2:
      min = 1 / 2
    elif min == 1:
      min = 1 / 4
    else:
      min = 1 / 12

  return (min, max)


def days_to_date(text):
  days_a = (text * 365)  # Tage berechen

  years = int(days_a / 365)
  months = int((days_a / 365 - years) * 12)

  days = int((((days_a / 365 - years) * 12) - months) * 30)

  return (years, months, days)


def print_result(title, absatz, fine, min_value, max_value):
  Anzahl_Verbrechen = 0
  Anzahl_Lebenslang = 0
  if min_value != 0 or max_value != 0:
    print(title, "Abs.", absatz, gesetz_bezeichnung)
    if law_text == True:
      print(paragraph.text)
    print(f"Geldstrafe: {fine}")
  if min_value < 1 and min_value > 0:
    x = int(min_value * 12)
    if x == 1:
      print(f"Min: {x} Monat")
    else:
      print(f"Min: {x} Monate")
  else:
    if min_value >= 1:
      print("Verbrechen: True")
      Anzahl_Verbrechen += 1
      print(f"Min: {min_value} Jahre")
  if num_reductions != 0:
    years, months, days = days_to_date(max_value)

    print(f"Max: {years} Jahre {months} Monate {days} Tage")

  else:
    if max_value == 1:
      print(f"Max: {max_value} Jahr")
    elif max_value == "Lebenslänglich":
      print("Max: Lebenslänglich")
      Anzahl_Lebenslang += 1
    elif max_value > 1:
      print(f"Max: {max_value} Jahre")
    elif max_value < 1 and max_value > 0:
      max_value = max_value * 12
      print(f"Max: {int(max_value)} Monate")


Loop_bol = True
print("Berechnung des Strafrahmens inklusive Rechnung mit Milderungsgründen für gewünschte Nomen")
while Loop_bol == True:
  # Gesetz auswählen

  gesetze = input("Geben Sie das Gesetz an, das analysiert werden soll. Drücken Sie Enter wenn das StGb ausgewählt werden soll. Ansonsten schreibe Hilfe: ")
  # Hilfe Anfrage beantworten
  if gesetze in help_words:
    print("Wenn Sie wissen wollen wie groß der Strafrahmen von einer  oder mehrere Strafnormen aus dem StGB oder aus dem Nebenstrafrecht ist können Sie einfach die Abkürzung oder den vollen Namen des Gesetzes eingeben")
    print("Ein Beispiel wäre etwa das BtMG oder Betäubungsmittelgesetz")
    gesetze = input("Wollen Sie eine Liste der verfügbaren Gesetze? y/n: ")

    # Liste aller Gesetze durchgehen
    if gesetze == "y":
      for law in laws:
        print(f"Abkürzung: {law[0]}: {law[1]} - Strafnormen: {law[2]}")
      gesetze = input("Wählen Sie nun das gewünschte Gesetz aus oder drücken Sie Enter: ")
    else:
      gesetze = input("Wählen Sie nun das gewünschte Gesetz aus: ")

  # Wenn kein Input, dann StGB auswählen
  for law in laws:
    if gesetze:
      if gesetze.lower() == law[0].lower() or gesetze.lower() == law[1].lower():
        gesetze = law[3]
        gesetz_bezeichnung = law[0]
    else:gesetze = "https://www.gesetze-im-internet.de/stgb/BJNR001270871.html"

  # URL der Website
  url = gesetze
  requests_cache.install_cache("Gesetze_Cache")
  response = requests.get(url)
  html = response.text
  soup = BeautifulSoup(html, 'lxml')

  Norm = input("Gebe die gewünschten Paragraphen des Gesetzes ein oder drücke Enter um alle auszugeben: ")

  num_reductions = input("Gibe Anzahl der Minderungsgründe an. Ansonsten drücke Enter:")  # Anzahl der Minderungen
  if num_reductions.isdigit() :
    num_reductions = int(num_reductions)
  else: num_reductions = 0

  law_text = input("Soll der Normtext ebenfalls abgedruckt werden? y/n: ")

  if law_text == "y": law_text = True
  else: law_text = False

  # Alle Absätze mit der Klasse "jurAbsatz" extrahieren
  paragraphs = []
  for p in  soup.find_all('div', class_='jurAbsatz'):
    if "Freiheitsstrafe" in p.text:
      paragraphs.append(p)

  # Inhalt von jnenbez ausgeben
  for paragraph in paragraphs:
    title = paragraph.parent.parent.parent.parent.find('span', class_='jnenbez')
    min_value, max_value, fine = text_to_min_max(paragraph.text)
    absatz = extract_absatz(paragraph.text)
    if title and (min_value != 0 or max_value != 0):
      num = extract_numbers_p(title.text)
      Norm_int = extract_numbers_p(Norm)

      for n in num:
        if Norm:
          for x in Norm_int:
            if n == x:
              if num_reductions:
                min_value, max_value = reduce_sentence(min_value, max_value)
                print_result(title.text, absatz, fine, min_value, max_value)
              else: print_result(title.text, absatz, fine, min_value, max_value)
        else:
          if num_reductions:
            min_value, max_value = reduce_sentence(min_value, max_value)
            print_result(title.text, absatz, fine, min_value, max_value)
          else:print_result(title.text, absatz, fine, min_value, max_value)
  print(f"Link zu dem Gesetzestext: {url}")
  Loop =input("Wollen Sie eine neue Berechnung durchführen? y/n:")
  if Loop != "y":
    Loop_bol = False
input("Press Enter to close the window.")