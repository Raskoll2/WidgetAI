import sys
import ctypes
import subprocess
import time
import json
import requests

from PySide2.QtWidgets import QApplication, QWidget, QLineEdit, QTextEdit
from PySide2.QtCore import Qt, QTimer
from PySide2.QtGui import QTextOption
from BlurWindow.blurWindow import blur

from g4f import ChatCompletion
from g4f.Provider import Vercel
from openai import api_key, Completion
import google.generativeai as palm


#Backend
def read_config():
    with open('config.txt', 'r') as f:
        lines = f.readlines()
    api_key = lines[1].strip()
    model = lines[4].strip()
    initial_prompt = lines[7].strip()
    palm_key = lines[34].strip()
    max_length = int(lines[37].strip())
    temp = float(lines[40].strip())
    ngrok = lines[43].strip()
    
    return api_key, model, initial_prompt, palm_key, max_length, temp, ngrok

def official(input_string, mode):
    api_key, model, initial_prompt, _, max_length, temp, _ = read_config()
    
    openai.api_key = api_key

    prompt = initial_prompt + '\nUser: ' + input_string + '\nAssistant: '

    
    try:
        response = openai.Completion.create(
            model=model,
            prompt=prompt,
            max_tokens=max_length,
            n=1,
            stop='User:',
            temperature=temp,
        )
        generated_text = response.choices[0].text.strip()

    except:
        generated_text = 'Something went wrong, probably an invalid API key'
        mode = 'free'

    return generated_text, mode
    

def gpt4f(prompt):
    _, _, initial_prompt, _, _, _, _= read_config()
    #prompt = initial_prompt + '\nUser: ' + input_string
    prompt = initial_prompt + 'User: ' + prompt



    try: response = g4f.ChatCompletion.create(
        model="gpt-3.5-turbo-16k",
        messages=[{"role": "user", "content": prompt}],
        stream=False,
        provider=Vercel
    )
    except:
        response = 'Rate limit :/'
        print('gpt4f no worky worky')
    return response


def Gpalm(input_string):
    _, _, initial_prompt, palm_key, max_length, temp, _ = read_config()
    palm.configure(api_key=palm_key)
    models = [m for m in palm.list_models() if 'generateText' in m.supported_generation_methods]
    model = models[0].name

    prompt = f'''<SYS>You are my assistant</SYS>

User: {input_string}

Assistant: '''

    completion = palm.generate_text(
        model=model,
        prompt=prompt,
        temperature=temp,
        max_output_tokens=max_length,
    )
    return completion.result


def local(input_string):
    _, _, initial_prompt, _, max_length, temp, ngrok = read_config()
    ini = "<SYS>{initial_prompt}</SYS>"
    prompt = f'''
### Instruction
{input_string}

### Response

'''
    
    headers = {
    'accept': 'application/json',
    'Content-Type': 'application/json',
    }
    print(ngrok)

    data = { "prompt": prompt,
             "temperature": temp,
             "max_context_length": 512,
             "max_length": max_length,
             "top_p": 0.9,
             "stop_sequence": ["\n\n\n\n\n", "### Instruction", "### Explanation", "### Tag", "### Context", "#### "],
             "rep_pen": 1.0,
             "use_world_info": False,
             "use_memory": False,
             "frmttriminc": False, #Trim incomplete sentences
             "singleline": False,
             "use_story": False,
             "quiet": False,}
    response = requests.post(ngrok + ':5001/api/v1/generate', headers=headers, data=json.dumps(data))

    response = response.json()['results'][0]['text']
    response = response.split('###')[0]
    print(response)
    return response

    

def ai(input_string, mode):
    mode = mode.lower().strip()
    
    if mode == 'paid' or mode == 'openai' or mode=='api':
        print(input_string, mode)
        generated_text, mode = official(input_string, mode)

    elif mode == 'palm' or mode == 'google' or mode=='bard':
        generated_text = Gpalm(input_string)
        
    elif mode == 'local' or mode == 'custom' or mode=='kobold':
        generated_text = local(input_string)
    
    else:
        generated_text = gpt4f(input_string)

    print(generated_text)

    start_idx = generated_text.find("~")
    end_idx = generated_text.rfind("~")
    start_idps = generated_text.find("~$")
    end_idps = generated_text.rfind("~$")

    if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
        command = generated_text[start_idx + 1:end_idx]
        command.strip()
        
        try:
            result = subprocess.run(command, shell=True, text=True, capture_output=True)
            generated_text += '\n\n' + result.stdout
        except Exception as e:
            generated_text = f"Error executing command: {str(e)}"


    elif start_idps != -1 and end_idps != -1 and start_idps < end_idps:
        command = generated_text[start_idps + 1:end_idps]
        command.strip()
        
        try:
            result = subprocess.run(command, shell=True, text=True, capture_output=True)
            generated_text += '\n\n' + result.stdout
        except Exception as e:
            generated_text = f"Error executing command: {str(e)}"
    else:
        with open("log.txt", "w", encoding="utf8", errors='ignore') as f:
            f.write(generated_text)
        f.close()
    return generated_text, mode


    

#Front end
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        with open('config.txt', 'r') as f:
            lines = f.readlines()
        self.mode = lines[25].strip()
        input_style = lines[10].strip()
        output_style = lines[13].strip()
        opacity = float(lines[16].strip())
        sizex = int(lines[19].strip())
        sizey = int(lines[22].strip())
        ibs1 = int(lines[28].strip())
        ibs2 = int(lines[29].strip())
        ibs3 = int(lines[30].strip())
        ibs4 = int(lines[31].strip())

        # Set window flags to customize the behavior
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint | Qt.Tool)

        # Set the translucent background and size
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(sizex, sizey)

        # Apply blur effect
        blur(self.winId())

        # Set the window opacity to 1 for no translucency
        self.setWindowOpacity(opacity)

        # Calculate the position for the bottom right corner with padding
        screen_geometry = QApplication.desktop().availableGeometry()
        self.move(screen_geometry.width() - self.width() - 50, screen_geometry.height() - self.height() - 50)

        # Create a text input box
        self.text_input = QLineEdit(self)
        self.text_input.setGeometry(ibs1, ibs2, sizex - ibs1 * 2, ibs4)
        self.text_input.setStyleSheet(input_style)

        # Create a QTextEdit to display the AI output
        self.ai_output_text = QTextEdit(self)
        self.ai_output_text.setGeometry(ibs1, ibs2 * 3, sizex - ibs1 * 2, sizey - ibs1 * 4)
        self.ai_output_text.setStyleSheet(output_style)
        self.ai_output_text.setWordWrapMode(QTextOption.WrapAnywhere)  # Allows text to wrap and create a vertical scrollbar if necessary
        self.ai_output_text.setAlignment(Qt.AlignTop)
        self.ai_output_text.setReadOnly(True)
        
        self.ai_output_text.verticalScrollBar().setStyleSheet("QScrollBar:vertical { background: #11111100; width: 10px; border-radius: 5px;}"
                                                            #"QScrollBar::handle:vertical { background: #fff; border-radius: 5px; min-height: 20px; }"
                                                            "QScrollBar::add-line:vertical { background: #21212100;}"
                                                            "QScrollBar::sub-line:vertical { background: #21212100;}"
                                                            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: #fff; }")
        

        # Connect the returnPressed signal to the handler function
        self.text_input.returnPressed.connect(self.handle_input)

        # Initialize variables for slow printing
        self.output_text = ""
        self.current_letter_index = 0
        self.print_timer = QTimer(self)
        self.print_timer.timeout.connect(self.print_next_letter)

    def handle_input(self):
        user_input = self.text_input.text()

        # Clear the stuff from the last query
        self.output_text = ""
        self.ai_output_text.clear()
        self.text_input.clear()
        output = ''

        #Functions
        if user_input.startswith('/api'):
            key = user_input.split(' ')[1]
            with open('config.txt', 'r') as f:
                lines = f.readlines()
                
            lines[1] = f'{key}\n'
            with open ('config.txt', 'w') as f:
                f.writelines(lines)
            output = 'Key successfully saved, now in api mode'
            self.model = 'paid'
        if user_input == '/model':
            with open('config.txt', 'r') as f:
                model = f.readlines()
            output = model[4]
            
        elif user_input.startswith('/model'):
            model = user_input.split(' ')[1]
            with open('config.txt', 'r') as f:
                lines = f.readlines()
                
            lines[4] = f'{model}\n'
            with open ('config.txt', 'w') as f:
                f.writelines(lines)
            output = 'Hello, this is model ' + str(model)

                
        elif user_input == '/mode':
            output = self.mode
            
        elif user_input.startswith('/mode'):
            if user_input.startswith('/model') == False:
                self.mode = user_input.split()[1]
                output = f'Now in {self.mode} mode'

        if user_input.startswith('/cmd'):
            command = user_input.split('/cmd')[1]
            ouput = subprocess.run(command, shell=True, text=True, capture_output=True) + 'L'
            print(output)
            
                
        if user_input == '/clear' or user_input == '/cls':
            output = ' '
                
        if user_input.lower().strip() == '/quit' or user_input.lower().strip() == '/kill' or user_input.lower().strip() == '/exit' or user_input.lower().strip() == '/cancell':
            quit()

        elif user_input.lower().strip() == '/restart' or user_input.lower().strip() == '/reboot':
            current_process = QProcess()
            current_process.startDetached(sys.executable, sys.argv)
            sys.exit(0)
            
        # Call all the good stuff
        if output == '':
            output, self.mode = ai(user_input, self.mode)

        # Slow print
        self.output_text = output
        self.current_letter_index = 0
        self.print_timer.start(5)  # set this to 0 to skip it more or less

    def print_next_letter(self):
        if self.current_letter_index < len(self.output_text):
            letter = self.output_text[self.current_letter_index]
            self.ai_output_text.insertPlainText(letter)
            self.current_letter_index += 1
        else:
            self.print_timer.stop()

if __name__ == '__main__':
    # Hide the command window
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec_())
