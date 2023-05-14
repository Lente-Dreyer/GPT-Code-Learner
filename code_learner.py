import gradio as gr
import json
import requests
import os
from termcolor import colored
import util
import tool_planner

API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

code_repo_path="./code_repo"

readme_info = """The README.md file is as follows: """ + util.get_readme(code_repo_path) + "\n\n"

repo_structure = """The repo structure is as follows: """ + util.get_repo_structure(code_repo_path) + "\n\n"

system_prompt = """Now you are an expert programmer and teacher of a code repository. 
    You will be asked to explain the code for a specific task in the repo.
    You will be asked to explain the code to a computer science student.
    You will be provided with some related code snippets related to the question, for example, the calling stacks, the code that calls the target functions, etc.
    Please think the explanation step-by-step, and explain the code in a way that the student can understand.
    Please answer the questions based on your knowledge, and you can also refer to the provided related code snippets.
    The README.md file and the repo structure are also available for your reference.
    If you need any details clarified, please ask questions until all issues are clarified. \n\n
""" + readme_info + repo_structure


def generate_response(system_msg, inputs, top_p, temperature, chat_counter, chatbot=[], history=[]):

    # Inputs are pre-processed with extra tools
    inputs = tool_planner.user_input_handler(inputs)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    if system_msg.strip() == '':
        initial_message = [{"role": "user", "content": f"{inputs}"}]
        multi_turn_message = []
    else:
        initial_message = [{"role": "system", "content": system_msg},
                           {"role": "user", "content": f"{inputs}"}]
        multi_turn_message = [{"role": "system", "content": system_msg}]

    if chat_counter == 0:
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": initial_message,
            "temperature": temperature,
            "top_p": top_p,
            "n": 1,
            "stream": True,
            "presence_penalty": 0,
            "frequency_penalty": 0,
        }
    else:
        messages = multi_turn_message
        for data in chatbot:
            user = {"role": "user", "content": data[0]}
            assistant = {"role": "assistant", "content": data[1]}
            messages.extend([user, assistant])
        temp = {"role": "user", "content": inputs}
        messages.append(temp)

        payload = {
            "model": "gpt-3.5-turbo",
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "n": 1,
            "stream": True,
            "presence_penalty": 0,
            "frequency_penalty": 0, }

    chat_counter += 1
    history.append(inputs)
    print(colored("Inputs: ", "green"), colored(inputs, "green"))
    response = requests.post(API_URL, headers=headers, json=payload, stream=True)
    token_counter = 0
    partial_words = ""

    response_complete = False

    counter = 0
    for chunk in response.iter_lines():
        if counter == 0:
            counter += 1
            continue

        if response_complete:
            print(colored("Response: ", "yellow"), colored(partial_words, "yellow"))

        if chunk.decode():
            chunk = chunk.decode()

            # Check if the chatbot is done generating the response
            try:
                if len(chunk) > 12 and "finish_reason" in json.loads(chunk[6:])['choices'][0]:
                    response_complete = json.loads(chunk[6:])['choices'][0].get("finish_reason", None) == "stop"
            except:
                print("Error in response_complete check")
                pass

            if len(chunk) > 12 and "content" in json.loads(chunk[6:])['choices'][0]['delta']:
                partial_words = partial_words + json.loads(chunk[6:])['choices'][0]["delta"]["content"]
                if token_counter == 0:
                    history.append(" " + partial_words)
                else:
                    history[-1] = partial_words
                chat = [(history[i], history[i + 1]) for i in range(0, len(history) - 1, 2)]
                token_counter += 1
                yield chat, history, chat_counter, response


def reset_textbox():
    return gr.update(value='')


def set_visible_false():
    return gr.update(visible=False)


def set_visible_true():
    return gr.update(visible=True)


def main():
    title = """<h1 align="center">GPT-Code-Learner</h1>"""

    system_msg_info = """A conversation could begin with a system message to gently instruct the assistant."""

    theme = gr.themes.Soft(text_size=gr.themes.sizes.text_md)

    with gr.Blocks(
            css="""#col_container { margin-left: auto; margin-right: auto;} #chatbot {height: 520px; overflow: auto;}""",
            theme=theme,
            title="GPT-Code-Learner",
    ) as demo:
        gr.HTML(title)

        with gr.Column(elem_id="col_container"):
            with gr.Accordion(label="System message:", open=False):
                system_msg = gr.Textbox(
                    label="Instruct the AI Assistant to set its beaviour",
                    info=system_msg_info,
                    value=system_prompt
                )
                accordion_msg = gr.HTML(
                    value="Refresh the app to reset system message",
                    visible=False
                )
            with gr.Row():
                with gr.Column(scale=10):
                    chatbot = gr.Chatbot(
                        label='GPT-Code-Learner',
                        elem_id="chatbot"
                    )

            state = gr.State([])
            with gr.Row():
                with gr.Column(scale=8):
                    inputs = gr.Textbox(
                        placeholder="What questions do you have for the repo?",
                        lines=1,
                        label="Type an input and press Enter"
                    )
                with gr.Column(scale=2):
                    b1 = gr.Button().style(full_width=True)

            with gr.Accordion(label="Examples", open=True):
                gr.Examples(
                    examples=[
                        ["Which function lunch the application in the repo?"],
                    ],
                    inputs=inputs)

            with gr.Accordion("Parameters", open=False):
                top_p = gr.Slider(minimum=-0, maximum=1.0, value=0.5, step=0.05, interactive=True,
                                  label="Top-p (nucleus sampling)", )
                temperature = gr.Slider(minimum=-0, maximum=5.0, value=0.5, step=0.1, interactive=True,
                                        label="Temperature", )
                chat_counter = gr.Number(value=0, visible=True, precision=0)

        inputs.submit(generate_response, [system_msg, inputs, top_p, temperature, chat_counter, chatbot, state],
                      [chatbot, state, chat_counter], )
        b1.click(generate_response, [system_msg, inputs, top_p, temperature, chat_counter, chatbot, state],
                 [chatbot, state, chat_counter], )

        inputs.submit(set_visible_false, [], [system_msg])
        b1.click(set_visible_false, [], [system_msg])
        inputs.submit(set_visible_true, [], [accordion_msg])
        b1.click(set_visible_true, [], [accordion_msg])

        b1.click(reset_textbox, [], [inputs])
        inputs.submit(reset_textbox, [], [inputs])

    demo.queue(max_size=99, concurrency_count=20).launch(debug=True)


if __name__ == "__main__":
    main()
