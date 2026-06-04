document.addEventListener(
    "DOMContentLoaded",
    function(){

        const form =
        document.getElementById(
            "chatForm"
        );

        const loading =
        document.getElementById(
            "loading"
        );

        const question =
        document.getElementById(
            "question"
        );

        const container =
        document.getElementById(
            "chatContainer"
        );

        question.focus();

        container.scrollTop =
        container.scrollHeight;

        form.addEventListener(
            "submit",
            function(){

                loading.style.display =
                "block";

            }
        );

    }
);