import sys
import ctypes
import subprocess
import time
import json
import requests
import os
import re

from PySide2.QtWidgets import (QApplication, QWidget, QLineEdit,
                               QTextEdit, QPushButton, QSlider,
                               QComboBox, QLabel, QMainWindow, QCheckBox)
from PySide2.QtCore import Qt, QTimer, QProcess, QPoint
from PySide2.QtGui import QTextOption, QFont, QIntValidator, QDragEnterEvent, QDropEvent
from BlurWindow.blurWindow import GlobalBlur

from g4f import ChatCompletion
from g4f.Provider import Vercel
from openai import api_key, Completion
import openai
import google.generativeai as palm




#--------- Config ------------------


def readConfig():
    with open("config.txt", "r") as file:
        lines = file.readlines()
    return lines

def write_to_config(line_number, value):
    lines = readConfig()
    lines[line_number] = value + "\n"
    with open("config.txt", "w") as file:
        file.writelines(lines)

class NewConfigWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setGeometry(200, 200, 400, 275)
        self.setWindowTitle("⚙")

        # Read values from the config file
        config_lines = readConfig()
        max_out_length_value = int(config_lines[1].strip()) 
        temperature_value = float(config_lines[4].strip())
        default_mode_value = config_lines[7].strip()
        prompt_template_value = config_lines[54].strip()

        # Create a container widget for the background
        bg_container = QWidget(self)
        bg_container.setGeometry(0, 0, 10000000, 10000000)
        bg_container.setObjectName("bg_container")

        # Create labels for the sliders and settings
        max_length_label = QLabel("Max Out Length", self)
        max_length_label.setGeometry(20, 10, 175, 20)
        
        max_length_slider = QSlider(Qt.Horizontal, self)
        max_length_slider.setGeometry(20, 40, 175, 20)
        max_length_slider.setRange(1, 512)
        max_length_slider.setValue(max_out_length_value)
        max_length_slider.valueChanged.connect(self.update_max_length)

        temperature_label = QLabel("Temperature", self)
        temperature_label.setGeometry(20, 70, 175, 20)
        
        temperature_slider = QSlider(Qt.Horizontal, self)
        temperature_slider.setGeometry(20, 100, 175, 20)
        temperature_slider.setRange(0, 200)  # Scale by 100 to get values from 0 to 2
        temperature_slider.setValue(temperature_value * 100)
        temperature_slider.valueChanged.connect(self.update_temperature)

        mode_label = QLabel("Default Mode", self)
        mode_label.setGeometry(20, 125, 175, 30)

        mode_dropdown = QComboBox(self)
        mode_dropdown.setGeometry(20, 160, 175, 30)
        mode_dropdown.addItems(["free", "google", "openai", "local"])
        mode_dropdown.setCurrentText(default_mode_value)
        mode_dropdown.currentTextChanged.connect(self.update_mode)

        initial_prompt_checkbox = QCheckBox("Use Initial Prompt", self)
        initial_prompt_checkbox.setGeometry(225, 20, 200, 25)
        initial_prompt_checkbox.setChecked(config_lines[51].strip() == 'True')  # Set the initial state
        initial_prompt_checkbox.stateChanged.connect(self.update_initial_prompt)

        
        prompt_label = QLabel("Initial Prompt", self)
        prompt_label.setGeometry(20, 195, 300, 30)
        
        prompt_input = QLineEdit(self)
        prompt_input.setGeometry(20, 225, 360, 30)
        prompt_input.setText(config_lines[10].strip())
        prompt_input.textChanged.connect(self.update_prompt)


        mode_label = QLabel("Prompt Format", self)
        mode_label.setGeometry(225, 55, 150, 30)

        mode_dropdown = QComboBox(self)
        mode_dropdown.setGeometry(225, 90, 150, 30)
        mode_dropdown.addItems(["Llama", "Alpaca", "Zephyr", "Vicuna", "Guanaco", "chatml", "openchat"])
        mode_dropdown.setCurrentText(prompt_template_value)
        mode_dropdown.currentTextChanged.connect(self.update_template)

        

        # Apply the blur effect
        self.setAttribute(Qt.WA_TranslucentBackground)
        GlobalBlur(self.winId())

        # Allow the window to be draggable
        self.drag_position = None

        # Apply styles using QSS
        self.setStyleSheet('''
            #bg_container {
                background-color: rgba(16, 16, 16, 0.7);
            }
            QLabel {
                color: white;
                font-size: 18px;
                font-family: Gadugi;
            }

            QSlider {
                background-color: transparent;
                selection-background-color: blue;
                selection-color: white;
                margin: 10px 0;
            }

            QLineEdit {
                background-color: black;
                color: white;
                font-size: 16px;
                font-family: Gadugi;
                border-radius: 15px;
                padding: auto 10px auto 10px;
            }
            QComboBox {
                background-color: black;
                color: white;
                font-size: 16px;
                font-family: Gadugi;
                border-radius: 15px;
                padding: auto 10px auto 30px;
            }
            QCheckBox {
                font-size: 18px;
                color: white;
                font-family: Gadugi;
            }
        ''')

    def update_max_length(self, value):
        write_to_config(1, str(value))

    def update_temperature(self, value):
        # Write the value to config.txt line 5 (scaling back to 0-2 range)
        temperature = value / 100.0
        write_to_config(4, str(temperature))

    def update_mode(self, value):
        write_to_config(7, value)

    def update_prompt(self, value):
        write_to_config(10, value)


    def update_initial_prompt(self, state):
        value = "True" if state == Qt.Checked else "False"
        write_to_config(51, value)

    def update_template(self, value):
        write_to_config(54, value)
        
#----------------------------------------------------------------------------------------
            
#Front end

class MyTextEdit(QTextEdit):
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return:
            if event.modifiers() == Qt.ShiftModifier:
                # Insert a new line when Shift+Enter is pressed
                cursor = self.textCursor()
                cursor.insertBlock()
            else:
                # Handle Enter key press without Shift (send input)
                user_input = self.toPlainText()
                mw.handle_input(user_input)
        else:
            super(MyTextEdit, self).keyPressEvent(event)
            
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

        with open('config.txt', 'r') as f:
            lines = f.readlines()
        self.mode = lines[7].strip()
        input_style = lines[22].strip()
        output_style = lines[25].strip()
        opacity = float(lines[44].strip())
        sizex = int(lines[35].strip())
        sizey = int(lines[36].strip())
        ibs1 = int(lines[39].strip())
        ibs2 = int(lines[40].strip())
        ibs4 = int(lines[41].strip())
        self.location = lines[28].strip()
        paddingx = float(lines[31].strip())
        paddingy = float(lines[32].strip())
        windowColor = lines[57].strip()
        

        # Set window flags to customize the behavior
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint | Qt.Tool)

        # Set the translucent background and size
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(sizex, sizey)

        # Apply blur effect
        GlobalBlur(self.winId(), windowColor)

        # Set the window opacity to 1 for no translucency
        self.setWindowOpacity(opacity)

        # Calculate the position for the bottom right corner with padding
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        if self.location.lower().strip() == "bottom-right":
            self.move(screen_geometry.width() - self.width() - paddingx, screen_geometry.height() - self.height() - paddingy)
        if self.location.lower().strip() == "bottom-left":
            self.move(paddingx, screen_geometry.height() - self.height() - paddingy)
        if self.location.lower().strip() == "top-right":
            self.move(screen_geometry.width() - self.width() - paddingx, paddingy)
        if self.location.lower().strip() == "top-left":
            self.move(paddingx, paddingy)
        if self.location.lower().strip() == "center":
            self.move(screen_geometry.width()//2 - self.width()//2 + paddingx, screen_geometry.height()//2 - self.height()//2 + paddingy)

        # Create a text input box
        self.text_input = MyTextEdit(self)
        self.text_input.setGeometry(ibs1, ibs2, sizex - ibs1 * 2, ibs4)
        self.text_input.setStyleSheet(input_style)

        # Create a QTextEdit to display the AI output
        self.ai_output_text = QTextEdit(self)
        self.ai_output_text.setGeometry(ibs1, ibs2 * 3, sizex - ibs1 * 2, sizey - ibs1 * 5)
        self.ai_output_text.setStyleSheet(output_style)
        self.ai_output_text.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)  # Allows text to wrap and create a vertical scrollbar if necessary
        self.ai_output_text.setAlignment(Qt.AlignTop)
        self.ai_output_text.setReadOnly(True)
        
        self.ai_output_text.verticalScrollBar().setStyleSheet("QScrollBar:vertical { background: #11111100; width: 10px; border-radius: 5px;}"
                                                            #"QScrollBar::handle:vertical { background: #fff; border-radius: 5px; min-height: 20px; }"
                                                            "QScrollBar::add-line:vertical { background: #21212100;}"
                                                            "QScrollBar::sub-line:vertical { background: #21212100;}"
                                                            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: #fff; }")


        self.press_button = QPushButton("Retry", self)
        self.press_button.setGeometry(ibs1, sizey - ibs2*1.5, (sizex - ibs1*2)//2.1, ibs4)
        self.press_button.clicked.connect(self.retryButton)

        
        button_style = """QPushButton { background-color: rgba(10, 10, 10, 0.5);
color: white;
font-size: 18px;
border-radius: 14px;
width: 20px;
padding: 0px;
font-family: Gadugi;}"""
        self.press_button.setStyleSheet(button_style)


        self.press_button2 = QPushButton("Config", self)
        self.press_button2.setGeometry(sizex // 1.9, sizey - ibs2*1.5, (sizex - ibs1*2)//2.1, ibs4)
        self.press_button2.clicked.connect(self.configButton)

        # Style the second button
        self.press_button2.setStyleSheet(button_style)


    def retryButton(self):
        default = "Write a creative poem, lymric, or haiku."
        self.output_text = ""
        self.ai_output_text.clear()
        self.text_input.clear()
        if self.UserInput != '':
            output = self.ai(self.UserInput, False)  # Send the user's input to the AI
        else:
            output = self.ai(default)
        self.output_text = output

    def configButton(self):
        new_config_window = NewConfigWindow(self)
        new_config_window.show()

    def dragEnterEvent(self, event: QDragEnterEvent):
        print('one')
        mime_data = event.mimeData()
        urls = mime_data.urls()
        if urls:
            for url in urls:
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.docx', '.pdf', '.txt', '.py')):
                    event.acceptProposedAction()
                    return

        text = mime_data.text()
        if text:
            # Check if the dropped text contains a supported file path
            file_path = text.strip()
            if file_path.lower().endswith(('.docx', '.pdf', '.txt', '.py')):
                event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        print('two')
        mime_data = event.mimeData()
        urls = mime_data.urls()
        dropped_text = mime_data.text()
        print(dropped_text)
        print('hmmm')

        # Handle dropped URLs
        if urls:
            print('urls:', urls)
            for url in urls:
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.docx', '.pdf', '.txt', '.py')):
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                        file_contents = file.read()
                    user_input = self.text_input.toPlainText()
                    user_input += 'file {' + file_contents + '}\n'
                    self.text_input.setPlainText(user_input)

        # Handle dropped text with supported file extensions
        if dropped_text.lower().endswith(('.docx', '.pdf', '.txt', '.py')):
            print('dt:', dropped_text)
            file_path = dropped_text.strip()
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                file_contents = file.read()
            user_input = self.text_input.toPlainText()
            user_input += file_contents
            self.text_input.setPlainText(user_input)

            
                
    def handle_input(self, user_input):
        self.UserInput = user_input
        if user_input != '':
            self.ai_output_text.clear()
            output = ''
        else:
            output = self.ai(self.ai_output_text, True)

        self.ai_output_text.insertPlainText(output)
        self.text_input.clear()


        #Functions
        if user_input.lower().strip().startswith('/ver'):
            output = "1.0.4"

        if user_input.lower().strip().startswith('hi'):
            output = " "
            self.ai_output_text.insertPlainText('Hello')
            time.sleep(0.001)

        if user_input.lower().strip() == '/initial':
            with open('config.txt', 'r') as f:
                lines = f.readlines()
            print(lines[51])
            output = ' '
            
        elif user_input.lower().strip().startswith('/initial'):
            ipromptBool = user_input.split('/initial ')[1]

            with open('config.txt', 'r') as f:
                lines = f.readlines()
                
            lines[51] = f'{ipromptBool}\n'
            with open ('config.txt', 'w') as f:
                f.writelines(lines)
            output = 'Use system prompt: {ipromptBool}'
            
            
        if user_input.startswith('/api'):
            key = user_input.split(' ')[1]
            with open('config.txt', 'r') as f:
                lines = f.readlines()
                
            lines[13] = f'{key}\n'
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
            output = subprocess.run(command, shell=True, text=True, capture_output=True).stdout
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
            output = self.ai(user_input, False)

        self.ai_output_text.insertPlainText(output)
        self.text_input.clear()


    #Backend
    def read_config(self):
        with open('config.txt', 'r') as f:
            lines = f.readlines()
        api_key = lines[13].strip()
        model = lines[16].strip()
        initial_prompt = lines[10].strip()
        palm_key = lines[19].strip()
        max_length = int(lines[1].strip())
        temp = float(lines[4].strip())
        ngrok = lines[47].strip()
        ipromptBool = eval(lines[51].strip())
        promptTemplate = lines[54].strip().lower()
        
        return api_key, model, initial_prompt, palm_key, max_length, temp, ngrok, ipromptBool, promptTemplate

    def official(self, input_string, mode):
        api_key, model, initial_prompt, _, max_length, temp, _, ipromptBool, _ = read_config()
        
        openai.api_key = api_key

        prompt = '\nUser: ' + input_string + '\nAssistant: '
        if ipromptBool:
            prompt = initial_prompt + prompt

        
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
        

    def gpt4f(self, prompt):
        _, _, initial_prompt, _, _, _, _, ipromptBool, _ = self.read_config()
        
        prompt = 'User: ' + prompt

        if ipromptBool:
            prompt = initial_prompt + prompt



        try: response = g4f.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            provider=Vercel
        )
        except:
            response = 'Rate limit :/'
            print('gpt4free no worky worky')
        return response


    def Gpalm(self, input_string):
        _, _, initial_prompt, palm_key, max_length, temp, _, ipromptBool, _ = self.read_config()
        palm.configure(api_key=palm_key)
        models = [m for m in palm.list_models() if 'generateText' in m.supported_generation_methods]
        model = models[0].name

        if ipromptBool: prompt = f'''<SYS>{initial_prompt}</SYS>

    User: {input_string}

    Assistant: '''
        else: prompt = f'''User: {input_string}

    Assistant: '''

        completion = palm.generate_text(
            model=model,
            prompt=prompt,
            temperature=temp,
            max_output_tokens=max_length,
        )
        return completion.result


    def local(self, input_string, Continue):
        _, _, initial_prompt, _, max_length, temp, ngrok, ipromptBool, promptTemplate = self.read_config()

        promptTemplate = promptTemplate.lower().strip()
        
        if promptTemplate == 'llama':
            #Llama
            ini = f'''[INST]<<SYS>>
    {initial_prompt}
    <</SYS>>
    '''
            prompt = f'''
    [INST]
    {input_string} [/INST]
    '''
        
        elif promptTemplate == 'vicuna':
            #Vicuna
            ini = initial_prompt + '\n'
            prompt = f'''
    User:
    {input_string}

    Assistant:

    '''
        
        elif promptTemplate == 'zephyr':
            #Zephyr
            ini = f"<|system|>{initial_prompt}</s>"
            prompt = f'''
    <|user|>
    {input_string}</s>
    <|assistant|>
    '''

        elif promptTemplate == 'alpaca':
            #Alpaca
            ini = initial_prompt + '\n'

            prompt = f'''
    ### Instruction:
    {input_string}

    ### Response:
    '''

        elif promptTemplate == 'guanaco':
            #Alpaca
            ini = initial_prompt + '\n'

            prompt = f'''
    ### Human:
    {input_string}

    ### Assistant:
    '''

        elif promptTemplate == 'chatml':
            #Alpaca
            ini = f'''<|im_start|>system
    {initial_prompt}<|im_end|>'''

            prompt = f'''
    <|im_start|>user
    {input_string}<|im_end|>
    <|im_start|>assistant
    '''

        elif promptTemplate == 'openchat':
            ini = 'GPT4 System: {initial_prompt}'
            prompt = f'''
GPT4 User: {input_string}<|end_of_turn|>GPT4 Assistant: '''

        
        
        else:
            ini = f'<SYS>{initial_prompt}</SYS>\n'
            prompt = f'''
    User:
    {input_string}

    Assistant:

    '''

        
        if ipromptBool:
            prompt = ini+prompt
            print('I though this would be better\n' + prompt)

        if Continue:
            prompt = input_string 
        
        headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        }

        data = { "prompt": prompt,
                 "temperature": temp,
                 "max_context_length": 100000,
                 "max_length": max_length,
                 "top_p": 0.8,
                 "stop_sequence": ["<", "\n\n\n", "### Instruction", "### Explanation", "### Tag", "### Context", "####", "User:", "Assistant:", "</s>", "<|", '</', 'Response:', 'emergency'],
                 "rep_pen": 1.2,
                 "use_world_info": False,
                 "use_memory": False,
                 "frmttriminc": False, #Trim incomplete sentences
                 "singleline": False,
                 "use_story": False,
                 "quiet": False,}
        if ngrok.startswith('tcp://'):
            query = str(ngrok.replace('tcp://', 'http://') + '/api/v1/generate')
            print(query)
            response = requests.post(query, headers=headers, data=json.dumps(data))
            
            
        else:
            query = str(ngrok + '/api/extra/generate/stream')
            print('2   ' + query)
            response = requests.post(query, headers=headers, data=json.dumps(data), stream=True)

        for line in response.iter_lines(decode_unicode=True):
            if line:
                tokens = re.findall(r'{"token": "([^"]+)"}', line)
                for token in tokens:
                    token = eval('"'+token+'"')
                    print(token, end='')
                    self.ai_output_text.insertPlainText(token)
                    app.processEvents()
                    
        return ' '

        

    def ai(self, input_string, Continue):
        mode = self.mode.lower().strip()
        
        if mode == 'paid' or mode == 'openai' or mode=='api':
            print(input_string, mode)
            generated_text, mode = self.official(input_string, mode)

        elif mode == 'palm' or mode == 'google' or mode=='bard':
            generated_text = self.Gpalm(input_string)
            
        elif mode == 'local' or mode == 'custom' or mode=='kobold':
            generated_text = self.local(input_string, Continue)
        
        else:
            generated_text = self.gpt4f(input_string)

        print(generated_text)

        #AI run commands
        start_idx = generated_text.find("~")
        end_idx = generated_text.rfind("~")

        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            command = generated_text[start_idx + 1:end_idx]
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
        return generated_text




if __name__ == '__main__':
    # Hide the command window
    try: os.system("xdotool search --class terminal windowunmap")
    except: pass
    
    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    
    sys.exit(app.exec_())
