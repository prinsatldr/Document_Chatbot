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
let recorder;
let chunks = [];
let voiceTranscript = "";

async function startRecording() {

    const stream =
        await navigator.mediaDevices.getUserMedia({
            audio: true
        });

    recorder = new MediaRecorder(stream);

    chunks = [];

    recorder.ondataavailable = function(event) {
        chunks.push(event.data);
    };

    recorder.start();

    console.log("Recording Started");

    document
        .getElementById("startRecord")
        .classList.add("recording");

}

document
    .getElementById("startRecord")
    .addEventListener(
        "click",
        startRecording
    );

function stopRecording() {

    document
        .getElementById("startRecord")
        .classList.remove("recording");

    console.log("Stop button clicked");

    recorder.stop();

    recorder.onstop = function() {

        console.log("Recorder stopped");

        const container =
            document.getElementById(
                "chatContainer"
            );

        container.innerHTML += `
            <div
                id="voiceLoading"
                class="message bot"
            >
                <div class="bubble">
                    Processing Voice...
                </div>
            </div>
        `;

        container.scrollTop =
            container.scrollHeight;

        const blob = new Blob(
            chunks,
            {
                type: "audio/webm"
            }
        );

        const formData = new FormData();

        formData.append(
            "audio",
            blob,
            "recording.webm"
        );

        fetch("/voice", {
            method: "POST",
            body: formData
        })
        .then(response => response.json())
        .then(data => {

            document
                .getElementById(
                    "voiceLoading"
                )
                .remove();

            container.innerHTML += `
                <div class="message user">
                    <div class="bubble">
                         ${data.transcript}
                    </div>
                </div>
            `;

            container.innerHTML += `
                <div class="message bot">
                    <div class="bubble">
                        ${data.answer}
                    </div>
                </div>
            `;

            container.scrollTop =
                container.scrollHeight;

            const speech =
                new SpeechSynthesisUtterance(
                    data.answer
                );

            speechSynthesis.speak(
                speech
            );

        })
        .catch(error => {

            console.error(error);

        });
        document
    .getElementById("startRecord")
    .disabled = false;

document
    .getElementById("stopRecord")
    .disabled = false;

    };
}

document
    .getElementById("stopRecord")
    .addEventListener(
        "click",
        stopRecording
    );