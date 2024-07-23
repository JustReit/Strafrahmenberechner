const input_gesetze = document.getElementById('gesetz');
const input_paragraphen = document.getElementById('paragraphen');
const showTextCheckbox = document.getElementById('showText');
input_paragraphen.value = '';
const resultsDiv = document.getElementById("results");
localStorage.removeItem('paragraph');
const maxSelectedTags = 50;
let  showTextChecked = false;
let gesetze = [];
let paragraphen = [];
let num_reductions = 0
let gesetze_tagify;
let paragraphen_tagify;
gesetze_tagify = new Tagify(input_gesetze, {
    whitelist: [],
    dropdown: {
        enabled: 0,
        maxItems: 200
    },
    duplicates: false,
    maxTags: maxSelectedTags

});
paragraphen_tagify = new Tagify(input_paragraphen, {
    whitelist: [],
    dropdown: {
        enabled: 0,
        maxItems: 200
    },
    duplicates: false,
    maxTags: maxSelectedTags
});

gesetze_tagify.on('change', SubmitGesetze);
paragraphen_tagify.on('change', SubmitParagraphen);




 async function SubmitGesetze() {
    const gesetzArray = gesetze_tagify.value.map(gesetz => ({ value: gesetz.value, url: gesetz.url }))
    paragraphen = [];
    paragraphen_tagify.settings.whitelist = [];
    await fetchParagraphen(gesetzArray);
    updateResults();
}

function SubmitParagraphen() {
    const paragraphenArray = paragraphen_tagify.value.map(paragraph => paragraph.value);
    localStorage.removeItem('paragraph');
    localStorage.setItem('paragraph', JSON.stringify(paragraphenArray));

}
async function fetchParagraphen(gesetzArray) {
    try {
        const response = await fetch("/api/paragraphen", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(gesetzArray),
        });

        const data = await response.json();

        console.log("data received");

        data.forEach(item => {
            const title = item.title;
            const absatz = item.absatz;
            const name = item.name;
            const minValue = item.minValue;
            const maxValue = item.maxValue;
            const fine = item.fine;
            const url = item.url;
            const lawtext = item.lawtext;
            const bezeichnung = item.bezeichnung;
            let text = "";
            if (bezeichnung) {
                text = `${title} Abs. ${absatz} ${name} (${bezeichnung})`;
            } else {
                text = `${title} Abs. ${absatz} ${name}`;
            }
            paragraphen.push({
                text,
                minValue,
                maxValue,
                fine,
                name,
                url,
                title,
                absatz,
                lawtext
            });
        });

        paragraphen_tagify.settings.whitelist = paragraphen.map(item => ({
            value: item.text,
            min: item.minValue,
            max: item.maxValue,
            fine: item.fine,
            name: item.name,
            url: item.url,
            title: item.title,
            absatz: item.absatz
        }));

        paragraphen_tagify.dropdown.show.call(paragraphen_tagify, input_paragraphen);
    } catch (error) {
        console.error(`Error fetching data: ${error.message}`);
    }
}

function fetchData() {
    fetch("/api/data")
        .then((response) => response.json())
        .then((data) => {
            gesetze = data.map(gesetzArray => ({
                identifier: gesetzArray[0],
                name: gesetzArray[1],
                section: gesetzArray[2],
                url: gesetzArray[3],
            }));
            gesetze_tagify.settings.whitelist = gesetze.map(gesetz => ({ value: gesetz.name, url: gesetz.url }));
            gesetze_tagify.dropdown.show.call(gesetze_tagify, input_gesetze);
        })
        .catch((error) => console.error(error));
}

function loadGesetze() {
    const tagObjects = gesetze.map(tag => ({ value: tag.name, url: tag.url }));
    gesetze_tagify.loadOriginalValues(tagObjects);
}

function removeAllTags() {
    gesetze = [];
    paragraphen = [];
}

function reduceSentence(min, max) {
    for (let i = 0; i < num_reductions; i++) {
        if (max === "Lebenslänglich") {
            max = 15;
            min = 3;
        } else {
            max = max * 0.75;
        }

        if (min === 10 || min === 5) {
            min = 2;
        } else if (min === 3 || min === 2) {
            min = 1 / 2;
        } else if (min === 1) {
            min = 1 / 4;
        } else {
            min = 1 / 12;
        }
    }

    return [min, max];
}

function yearsToMonthsAndDays(num) {
    const years = Math.floor(num);
    const remainingMonths = (num - years) * 12;
    const months = Math.floor(remainingMonths);
    const remainingDays = (remainingMonths - months) * 30; // Assuming 30 days per month
    const days = Math.floor(remainingDays);
    return [years, months, days];
}




function createParagraphDiv() {
    const paragraphDiv = document.createElement('div');
    paragraphDiv.classList.add('paragraph-container', 'col-6', 'col-sm-4', 'col-md-3', 'col-lg-2', 'mb-3');

    paragraphDiv.addEventListener('mouseenter', () => {
        if (showTextChecked) {
            paragraphDiv.style.maxHeight = 'none';
        }
    });

    paragraphDiv.addEventListener('mouseleave', () => {
        if (showTextChecked) {
            paragraphDiv.style.maxHeight = '20rem';
        }
    });

    return paragraphDiv;
}

function printTitle(paragraphDiv, title) {
    paragraphDiv.innerHTML += `<p class="paragraph-title"><strong>${title}</strong></p>`;
}


function printMinMaxValues(paragraphDiv, min_value, max_value) {
    if (num_reductions !== 0) {
        [min_value,max_value] = reduceSentence(min_value, max_value);
    }

    if (min_value < 1 && min_value > 0) {
        paragraphDiv.innerHTML += `<p>Verbrechen: Nein</p>`;
        paragraphDiv.innerHTML += `<p>Min: ${min_value * 12} Monate</p>`;
        paragraphDiv.dataset.felony = false;
    } else if (min_value >= 1) {
        paragraphDiv.innerHTML += `<p>Verbrechen: Ja</p>`;
        paragraphDiv.innerHTML += `<p>Min: ${min_value} Jahre</p>`;
        paragraphDiv.dataset.felony = false;
    }
    if (num_reductions !== 0) {
        let [years, months, days] = yearsToMonthsAndDays(max_value);
        paragraphDiv.innerHTML += `<p>Max: ${years} Jahre ${months} Monate ${days} Tage</p>`;
    }else
    {
    if (max_value === 1) {
        paragraphDiv.innerHTML += `<p>Max: ${max_value} Jahr</p>`;
    } else if (max_value === "Lebenslänglich") {
        paragraphDiv.innerHTML += `<p>Max: Lebenslänglich</p>`;
    } else if (max_value > 1) {
        paragraphDiv.innerHTML += `<p>Max: ${max_value} Jahre</p>`;
    } else if (max_value < 1 && max_value > 0) {
        max_value *= 12;
        paragraphDiv.innerHTML += `<p>Max: ${parseInt(max_value)} Monate</p>`;
    }
    }
}


function printFineInfo(paragraphDiv, fine) {
    paragraphDiv.innerHTML += `<p>${fine ? "Geldstrafe: möglich" : "Geldstrafe: nicht möglich"}</p>`;
}

function printLawText(paragraphDiv, showTextChecked, lawtext, url) {
    const lawtextParagraph = document.createElement('p');
    lawtextParagraph.classList.add('lawtext-paragraph');

    // Always set the content
    lawtextParagraph.textContent = `Gesetzestext: ${lawtext}`;
    lawtextParagraph.innerHTML += `<div>Link: <a href="${url}">${url}</a></div>`;
    lawtextParagraph.style.display = "none";
    if (showTextChecked){
        lawtextParagraph.style.display = "block";
    }

    paragraphDiv.appendChild(lawtextParagraph);
}

function printResult(title, absatz, fine, min_value, max_value, lawtext, url, resultsDiv) {
    const paragraphDiv = createParagraphDiv();
    printTitle(paragraphDiv, title);
    printMinMaxValues(paragraphDiv,min_value, max_value);
    printFineInfo(paragraphDiv, fine);
    printLawText(paragraphDiv, showTextCheckbox.checked, lawtext, url);
    paragraphDiv.dataset.minValue = min_value;
    paragraphDiv.dataset.maxValue = max_value;
    paragraphDiv.dataset.fine = fine;
    paragraphDiv.dataset.law =url;
    paragraphDiv.dataset.title =title;
    resultsDiv.appendChild(paragraphDiv);
}

showTextCheckbox.addEventListener('change', function () {
     showTextChecked = this.checked;

    // Toggle visibility of law text paragraphs
    const lawtextParagraphs = document.querySelectorAll('.lawtext-paragraph');

    lawtextParagraphs.forEach(lawtextParagraph => {

        if (showTextChecked){
            lawtextParagraph.style.display = "block";
        }else{
            lawtextParagraph.style.display = "none";
        }
    });
});


document.getElementById("calculate").addEventListener("click", async function () {
    num_reductions = parseInt(document.getElementById("minderungen").value, 10) || 0;

    resultsDiv.innerHTML = ''; // Clear previous results


    const storedParagraphs = JSON.parse(localStorage.getItem('paragraph')) || [];
    if(input_gesetze.value === '' ) { //Print all paragraphs from all laws
        const  div = document.createElement("div");
        div.classList.add('d-flex', 'justify-content-center');
        const spinner = document.createElement('div');
        spinner.classList.add('spinner-grow', 'text-primary', 'pd-8');
        spinner.setAttribute('role', 'status');
        div.appendChild(spinner);
        resultsDiv.appendChild(div);
        const gesetzArray = gesetze.map(gesetz => ({ value: gesetz.name, url: gesetz.url }))
        await fetchParagraphen(gesetzArray);
        spinner.remove();
    }
    const selectedParagraphs = paragraphen.filter(paragraph => storedParagraphs.includes(paragraph.text));
    if(selectedParagraphs.length !== 0){ //Print only selected paragraphs
        selectedParagraphs.forEach((paragraph) => {
            printResult(
                paragraph.text,
                paragraph.absatz,
                paragraph.fine,
                paragraph.minValue,
                paragraph.maxValue,
                paragraph.lawtext,
                paragraph.url,
                resultsDiv
            );
        });
    }else{
        paragraphen.forEach((paragraph) => { //Print all paragraphs in the paragraph list
            printResult(
                paragraph.text,
                paragraph.absatz,
                paragraph.fine,
                paragraph.minValue,
                paragraph.maxValue,
                paragraph.lawtext,
                paragraph.url,
                resultsDiv
            );
        });
    }

});
document.getElementById("clear").addEventListener("click",  function () {
     clearResults();
});

 function clearResults() {
    input_gesetze.value = '';
    input_paragraphen.value = '';
    document.getElementById("minderungen").value = '';
    resultsDiv.innerHTML = ''; // Clear previous results
    localStorage.removeItem('paragraph');
    paragraphen.length = 0;
    paragraphen_tagify.settings.whitelist = [];

}

document.addEventListener("DOMContentLoaded",  function() {
    // Code to be executed after the DOM has fully loaded
    removeAllTags();
    fetchData();
    loadGesetze();
     clearResults(); // Use await if you want to make use of asynchronous features in the future
});
document.getElementById("minderungen").addEventListener('change', function() {
    num_reductions = parseInt(this.value, 10) || 0;

    // Update results based on new values
    updateResults();
});

function updateResults() {
    resultsDiv.innerHTML = ''; // Clear previous results

    paragraphen.forEach((paragraph) => {
        const paragraphDiv = createParagraphDiv();
        printTitle(paragraphDiv, paragraph.text);
        printMinMaxValues(paragraphDiv, paragraph.minValue, paragraph.maxValue);
        printFineInfo(paragraphDiv, paragraph.fine);
        printLawText(paragraphDiv, showTextCheckbox.checked, paragraph.lawtext, paragraph.url);

        resultsDiv.appendChild(paragraphDiv);
    });
}

document.getElementById("search").addEventListener("input", function (e) {
    const searchText = e.target.value.toLowerCase();
    const items = Array.from(resultsDiv.children);

    Array.from(items).forEach((item) => {
        const paragraphTitleElement = item.querySelector('.paragraph-title');
        const lawtextParagraphElement = item.querySelector('.lawtext-paragraph');

        if (paragraphTitleElement && lawtextParagraphElement) {
            const paragraphText = paragraphTitleElement.innerText.toLowerCase();
            const lawtext = lawtextParagraphElement ? lawtextParagraphElement.innerText.toLowerCase() : '';

            if (paragraphText.indexOf(searchText) !== -1 || lawtext.indexOf(searchText) !== -1) {
                item.style.display = "block";
            } else {
                item.style.display = "none";
            }
        } else {
            // Handle the case when paragraphTitleElement is not found
            console.error("Required elements not found within the item:", item);
        }
    });
});

function sortItems(sortMethod) {
    // Get the list of items
    const items = Array.from(resultsDiv.children);
    // Sort the items based on the selected sorting method
    console.log(items);
    const sortedItems = items.sort((a, b) => {

        let itemA = a.dataset[sortMethod];
        let itemB = b.dataset[sortMethod];
        if (sortMethod === 'minValue') {
            console.log(parseFloat(itemB));
            // Convert values to numbers for numeric comparison
            return parseFloat(itemA) - parseFloat(itemB);
        }
       else if ( sortMethod === 'maxValue') {
           if(itemB === "Lebenslänglich"){
               itemB = 20;
           }
            if(itemA === "Lebenslänglich"){
                itemA = 20;
            }
            // Convert values to numbers for numeric comparison
            return parseInt(itemB, 10) - parseInt(itemA, 10);
        }
        else {
            // For other fields, use string comparison
            return itemA.localeCompare(itemB);
        }
    });

    // Clear the current list
    resultsDiv.innerHTML = '';

    // Append the sorted items to the list
    sortedItems.forEach(item => {
        resultsDiv.appendChild(item);
    });
}