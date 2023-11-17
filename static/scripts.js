    // Filter form show/hide js
    $(document).ready(function(){
        $(".filter-btn").click(function(){
            $(".filter-form").fadeToggle('slow', function(){
                // // Toggle the visibility of the submit button and footer
                $("#submit, footer").toggle();
            });
        });
    });