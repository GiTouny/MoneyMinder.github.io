const sideMenu = document.querySelector('aside');
const menuBtn = document.querySelector('#menu-btn');
const closeBtn = document.querySelector('#close-btn');
const themeToggler = document.querySelector('.theme-toggler');
const isDarkMode = localStorage.getItem('dark-theme-variables') === 'true';

// show sidebar
menuBtn.addEventListener('click', () => {
    sideMenu.style.display = 'block';
});

// close sidebar
closeBtn.addEventListener('click', () => {
    sideMenu.style.display = 'none';
});

// add/remove sidebar active
let links = document.querySelectorAll('.sidebar a');
let currentURL = window.location.href;

links.forEach(link => {
    if (link.href === currentURL) {
        link.classList.add('active');
    }
});

document.addEventListener('DOMContentLoaded', function () {
    if (isDarkMode) {
        document.body.classList.add('dark-theme-variables');
        themeToggler.querySelector('span:nth-child(1)').classList.toggle('active');
        themeToggler.querySelector('span:nth-child(2)').classList.toggle('active');
    }
});

// change theme
themeToggler.addEventListener('click', () => {
    document.body.classList.toggle('dark-theme-variables');
    themeToggler.querySelector('span:nth-child(1)').classList.toggle('active');
    themeToggler.querySelector('span:nth-child(2)').classList.toggle('active');
    localStorage.setItem('dark-theme-variables', document.body.classList.contains('dark-theme-variables'));
});

// Drag or drop file image
var dropZones = document.querySelectorAll('.card-photo');

dropZones.forEach(function(dropZone, index) {
    dropZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        dropZone.classList.add('card-photo--over');
    });

    dropZone.addEventListener('dragleave', function() {
        dropZone.classList.remove('card-photo--over');
    });

    dropZone.addEventListener('drop', function(e) {
        e.preventDefault();
        dropZone.classList.remove('card-photo--over');

        handleFiles(e.dataTransfer.files, dropZone, index + 1); // Index + 1 for unique ID
    });
});

var fileInputs = document.querySelectorAll('.drop-zone-input');

fileInputs.forEach(function(fileInput, index) {
    fileInput.addEventListener('change', function() {
        handleFiles(fileInput.files, dropZones[index], index + 1); // Index + 1 for unique ID
    });
});

function handleFiles(files, dropZone, index) {
    if (files.length > 0) {
        var reader = new FileReader();

        reader.readAsDataURL(files[0]);

        reader.onload = function(e) {
            dropZone.style.backgroundImage = "url('" + e.target.result + "')";
            dropZone.style.border = "none";
            dropZone.innerHTML = ""; // Remove prompt text

            // You can use the 'index' parameter to distinguish between different drop zones
            console.log("File dropped for card at index " + index);
        }
    }
}
