document.addEventListener(
    "DOMContentLoaded",
    function () {

        const form =
        document.getElementById(
            "chatForm"
        );

        const question =
        document.getElementById(
            "question"
        );

        const container =
        document.getElementById(
            "chatContainer"
        );

        const loading =
        document.getElementById(
            "loading"
        );

        form.addEventListener(
            "submit",
            async function(e){

                e.preventDefault();

                const text =
                question.value.trim();

                if(
                    text === ""
                ){
                    return;
                }

                container.innerHTML += `
                    <div class="message user">
                        <div class="bubble">
                            ${text}
                        </div>
                    </div>
                `;

                container.scrollTop =
                container.scrollHeight;

                question.value = "";

                loading.style.display =
                "flex";

                container.scrollTop =
                container.scrollHeight;

                const formData =
                new FormData();

                formData.append(
                    "question",
                    text
                );

                try{

                    const response =
                    await fetch(
                        "/search",
                        {
                            method:"POST",
                            body:formData
                        }
                    );

                    const data =
                    await response.json();

                    loading.style.display =
                    "none";

                    container.innerHTML += `
                        <div class="message bot">
                            <div class="bubble">
                                ${data.answer}
                            </div>
                        </div>
                    `;

                    container.scrollTop =
                    container.scrollHeight;

                }
                catch(error){

                    loading.style.display =
                    "none";

                    container.innerHTML += `
                        <div class="message bot">
                            <div class="bubble">
                                Error getting response.
                            </div>
                        </div>
                    `;

                }

            }
        );

    }
);