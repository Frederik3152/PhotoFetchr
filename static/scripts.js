    // Filter form show/hide js
    $(document).ready(function(){
        $(".filter-btn").click(function(){
            $(".filter-form").fadeToggle('slow', function(){
                // // Toggle the visibility of the submit button and footer
                $("#submit, footer, .welcome-section, .button, #random-picture").toggle();
            });
        });
    });
 
// Toggle the instructions on the "Hvordan virker det" button
function showInstructions() {
    var instructionsContainer = document.getElementById('instructions-container');
    instructionsContainer.classList.toggle('hidden');

    var instructionExplanations = document.getElementById('instruction-explanations');
    instructionExplanations.style.display = instructionsContainer.classList.contains('hidden') ? 'none' : 'block';
  }

function showRandomPicture() {
    // Fetch a random picture URL from the Flask backend
    fetch('/random-pic')
        .then(response => response.json())
        .then(data => {
            // Update the #random-picture element with the image
            document.getElementById('random-picture').innerHTML = `<img src="${data.imageUrl}" alt="Random Picture" style="width: 100%; height: 80%; padding: 10px;">`;
        })}

// Rotate the picture orientation
let rotation = 0;
// How much to rotate the image at a time
const angle = 90;
function rotateImage() {
    // Ensure angle range of 0 to 359 with "%" operator
    rotation = (rotation + angle) % 360;
    var carouselImages = document.querySelectorAll('.carousel-inner img');
    var gridImages = document.querySelectorAll('.grid-view img');
    var enlargedImage = document.getElementById('enlargedImg');
    
    carouselImages.forEach(function (image) {
        // Apply the rotation transformation
        image.style.transform = `rotate(${rotation}deg)`;
    });

    gridImages.forEach(function (image) {
        // Apply the rotation transformation
        image.style.transform = `rotate(${rotation}deg)`;
    });

    if (enlargedImage) {
        // Apply the rotation transformation
        enlargedImage.style.transform = `rotate(${rotation}deg)`;
    }
}
// Toggle the view between the grid and carousel views in the result page
function toggleView() {
    var carousel = $('#carouselExampleControls');
    var gridView = $('#gridView');

    if (carousel.is(':visible')) {
        carousel.hide();
        gridView.show();
    } else {
        carousel.show();
        gridView.hide();
    }
}
// Opening the Bootstrap modal when a picture is clicked in the grid view 
function openModal(imageUrl) {
    $('#enlargedImg').attr('src', imageUrl);
    $('#imageModal').modal('show');
}

document.querySelectorAll('.photo-card').forEach(card => {
  card.addEventListener('click', () => {
    window.location.href = card.dataset.href;
  });
});