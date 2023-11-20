    // Filter form show/hide js
    $(document).ready(function(){
        $(".filter-btn").click(function(){
            $(".filter-form").fadeToggle('slow', function(){
                // // Toggle the visibility of the submit button and footer
                $("#submit, footer, .welcome-section, .button, #random-picture").toggle();
            });
        });
    });

    function showRandomPicture() {
        // Fetch a random picture URL from the Flask backend
        fetch('/random-pic')
            .then(response => response.json())
            .then(data => {
                // Update the #random-picture element with the image
                document.getElementById('random-picture').innerHTML = `<img src="${data.imageUrl}" alt="Random Picture" style="width: 100%; height: 80%; padding: 10px;">`;
            })}