import os
import sys
import json
import zipfile
import webbrowser
import requests
import subprocess
import platform
import shutil
from pathlib import Path
from datetime import datetime
import minecraft_launcher_lib

MINECRAFT_DIR = str(Path.home() / ".minecraft")
LAUNCHER_DATA_DIR = str(Path.home() / ".cobalt_launcher_nano")
CONFIG_FILE = os.path.join(LAUNCHER_DATA_DIR, "config.json")
NOTES_FILE = os.path.join(LAUNCHER_DATA_DIR, "notes.txt")
ACCOUNTS_FILE = os.path.join(LAUNCHER_DATA_DIR, "accounts.json")
JAVA_DIR = os.path.join(LAUNCHER_DATA_DIR, "java")

os.makedirs(LAUNCHER_DATA_DIR, exist_ok=True)
os.makedirs(JAVA_DIR, exist_ok=True)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"java_args": "-Xmx2G -Xms1G", "selected_version": None, "current_account": None}
    return {"java_args": "-Xmx2G -Xms1G", "selected_version": None, "current_account": None}

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_accounts(accounts):
    with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(accounts, f, indent=4, ensure_ascii=False)

def add_offline_account(username):
    accounts = load_accounts()
    account = {
        "id": len(accounts) + 1,
        "username": username,
        "type": "offline",
        "created_at": datetime.now().isoformat()
    }
    accounts.append(account)
    save_accounts(accounts)
    return account

def delete_account(account_id):
    accounts = load_accounts()
    accounts = [acc for acc in accounts if acc["id"] != account_id]
    save_accounts(accounts)
    return True

def get_account_by_id(account_id):
    accounts = load_accounts()
    for account in accounts:
        if account["id"] == account_id:
            return account
    return None

def open_url(url):
    try:
        webbrowser.open(url)
        print("Ссылка открывается в браузере...")
    except Exception as e:
        print(f"Ошибка открытия ссылки: {e}")

class ScrollableList:
    def __init__(self, items, page_size=10):
        self.items = items
        self.page_size = page_size
        self.current_page = 0
    
    def display_page(self):
        start_idx = self.current_page * self.page_size
        end_idx = start_idx + self.page_size
        page_items = self.items[start_idx:end_idx]
        
        print(f"Страница {self.current_page + 1}/{(len(self.items) + self.page_size - 1) // self.page_size}")
        print("--------------------------------------------------")
        
        for i, item in enumerate(page_items, start=1):
            print(f"{start_idx + i:3}. {item}")
        
        print("--------------------------------------------------")
    
    def navigate(self):
        while True:
            self.display_page()
            print("\nКоманды:")
            print("n - следующая страница")
            print("p - предыдущая страница")
            print("число - выбрать элемент")
            print("q - выйти")
            
            choice = input("Выберите: ").lower()
            
            if choice == 'n':
                if (self.current_page + 1) * self.page_size < len(self.items):
                    self.current_page += 1
                else:
                    print("Это последняя страница")
            elif choice == 'p':
                if self.current_page > 0:
                    self.current_page -= 1
                else:
                    print("Это первая страница")
            elif choice == 'q':
                return None
            elif choice.isdigit():
                idx = int(choice) - 1
                actual_idx = self.current_page * self.page_size + idx
                if 0 <= actual_idx < len(self.items):
                    return actual_idx
                else:
                    print("Неверный номер")
            else:
                print("Неверная команда")

def print_banner():
    banner = """
╔═══════════════════════════════════════════╗
║         Cobalt Launcher Nano 0.5 Alpha    ║
╠═══════════════════════════════════════════╣
║ Автор: M1rotvorets                        ║
║ Соавторы: WaterBucket, Nosok              ║
║ Сайт: https://m1r0tv0rets.github.io       ║
╚═══════════════════════════════════════════╝
    """
    print(banner)

def print_help():
    help_text = """
╔══════════════════════════════════════════════════════════╗
║                   ДОСТУПНЫЕ КОМАНДЫ                      ║
╠══════════════════════════════════════════════════════════╣
║ помощь      - Показать это сообщение                     ║
║ акк         - Управление аккаунтами (прокрутка)          ║
║ вер         - Список версий Minecraft (прокрутка)        ║
║ установить  - Установить версию                          ║
║ запуск      - Запустить Minecraft                        ║
║ арг         - Настройка аргументов Java                  ║
║ память      - Установить объем памяти                    ║
║ новости     - Новости Minecraft                          ║
║ заметка     - Добавить заметку                           ║
║ заметки     - Показать все заметки                       ║
║ бэкап       - Создать резервную копию                    ║
║ папка       - Открыть папку Minecraft                    ║
║ лог         - Скопировать последний лог на рабочий стол  ║
║ выход       - Выйти из лаунчера                          ║
╚══════════════════════════════════════════════════════════╝

Помощь с проблемами:
Диагностика лога: https://m1r0tv0rets.github.io/cobalt_launcher/dignostic.html
Поддержка: https://t.me/tl_chat_ru/687311
Репозиторий: https://github.com/m1r0tv0rets/cobalt_launcher
    """
    print(help_text)

def manage_accounts_scrollable():
    accounts = load_accounts()
    config = load_config()
    
    if not accounts:
        print("Аккаунты не найдены")
        choice = input("Добавить оффлайн аккаунт? (y/n): ").lower()
        if choice == 'y':
            username = input("Введите имя пользователя: ")
            account = add_offline_account(username)
            config["current_account"] = account["id"]
            save_config(config)
            print(f"Аккаунт '{username}' добавлен!")
        return
    
    account_list = []
    for acc in accounts:
        status = "✓" if config.get("current_account") == acc["id"] else " "
        account_list.append(f"{status} {acc['username']} ({acc['type']}) - ID: {acc['id']}")
    
    scroll_list = ScrollableList(account_list, page_size=15)
    
    print("╔══════════════════════════════════════════════╗")
    print("║           УПРАВЛЕНИЕ АККАУНТАМИ              ║")
    print("╚══════════════════════════════════════════════╝")
    
    while True:
        print("\nВыберите действие:")
        print("1. Просмотр аккаунтов (прокрутка)")
        print("2. Добавить оффлайн аккаунт")
        print("3. Удалить аккаунт")
        print("4. Выбрать текущий аккаунт")
        print("5. Назад")
        
        choice = input("Выберите: ")
        
        if choice == '1':
            selected_idx = scroll_list.navigate()
            if selected_idx is not None:
                selected_acc = accounts[selected_idx]
                print(f"\nВыбран аккаунт:")
                print(f"  Имя: {selected_acc['username']}")
                print(f"  Тип: {selected_acc['type']}")
                print(f"  ID: {selected_acc['id']}")
                print(f"  Создан: {selected_acc['created_at']}")
        
        elif choice == '2':
            username = input("Введите имя пользователя: ")
            if username:
                account = add_offline_account(username)
                print(f"Аккаунт '{username}' добавлен с ID {account['id']}!")
        
        elif choice == '3':
            acc_id = input("Введите ID аккаунта для удаления: ")
            if acc_id.isdigit():
                if delete_account(int(acc_id)):
                    print("Аккаунт удален!")
                else:
                    print("Аккаунт не найден!")
        
        elif choice == '4':
            acc_id = input("Введите ID аккаунта для выбора: ")
            if acc_id.isdigit():
                acc = get_account_by_id(int(acc_id))
                if acc:
                    config["current_account"] = acc["id"]
                    save_config(config)
                    print(f"Текущий аккаунт: {acc['username']}")
                else:
                    print("Аккаунт не найден!")
        
        elif choice == '5':
            break
        else:
            print("Неверный выбор!")

def list_versions_scrollable():
    print("Получение списка версий...")
    
    try:
        versions = minecraft_launcher_lib.utils.get_available_versions(MINECRAFT_DIR)
        version_list = [f"{v['id']} ({v['type']})" for v in versions]
        
        scroll_list = ScrollableList(version_list[::-1], page_size=15)
        
        print("╔══════════════════════════════════════════════╗")
        print("║           ВЕРСИИ MINECRAFT                   ║")
        print("╚══════════════════════════════════════════════╝")
        
        selected_idx = scroll_list.navigate()
        if selected_idx is not None:
            selected_version = versions[len(versions)-1-selected_idx]['id']
            print(f"\nВыбрана версия: {selected_version}")
            
            choice = input("Установить эту версию? (y/n): ").lower()
            if choice == 'y':
                install_version(selected_version)
    
    except Exception as e:
        print(f"Ошибка получения списка версий: {e}")

def install_version(version):
    print(f"Установка версии {version}...")
    
    try:
        minecraft_launcher_lib.install.install_minecraft_version(version, MINECRAFT_DIR)
        
        config = load_config()
        config["selected_version"] = version
        save_config(config)
        
        print(f"Версия {version} успешно установлена!")
        
    except Exception as e:
        print(f"Ошибка установки: {e}")

def set_java_args():
    config = load_config()
    current_args = config.get("java_args", "-Xmx2G -Xms1G")
    
    print(f"\nТекущие аргументы Java: {current_args}")
    print("Примеры:")
    print("  -Xmx4G -Xms2G - 4GB максимум, 2GB минимум")
    print("  -Xmx8G -Xms4G -XX:+UseG1GC - с оптимизацией G1GC")
    
    new_args = input("\nВведите новые аргументы (Enter для отмены): ")
    
    if new_args:
        config["java_args"] = new_args
        save_config(config)
        print("Аргументы обновлены!")

def set_memory(gb):
    if not gb.isdigit():
        print("Укажите количество гигабайт числом")
        return
    
    gb_int = int(gb)
    if gb_int < 1 or gb_int > 32:
        print("Укажите значение от 1 до 32 GB")
        return
    
    config = load_config()
    current_args = config.get("java_args", "")
    
    import re
    new_args = re.sub(r"-Xmx\d+G", f"-Xmx{gb}G", current_args)
    new_args = re.sub(r"-Xms\d+G", f"-Xms{gb}G", new_args)
    
    if "-Xmx" not in new_args:
        new_args = f"-Xmx{gb}G -Xms{gb}G " + new_args
    
    config["java_args"] = new_args.strip()
    save_config(config)
    print(f"Память установлена на {gb}GB")

def launch_minecraft():
    config = load_config()
    
    if not config.get("selected_version"):
        print("Сначала установите версию Minecraft!")
        print("Используйте команду 'вер' для выбора версии")
        return
    
    accounts = load_accounts()
    current_account_id = config.get("current_account")
    
    if not current_account_id or not any(a["id"] == current_account_id for a in accounts):
        print("Сначала настройте аккаунт!")
        print("Используйте команду 'акк' для управления аккаунтами")
        return
    
    account = next((a for a in accounts if a["id"] == current_account_id), None)
    if not account:
        print("Аккаунт не найден!")
        return
    
    version = config["selected_version"]
    username = account["username"]
    
    print("╔══════════════════════════════════════════════╗")
    print("║           ЗАПУСК MINECRAFT                   ║")
    print("╠══════════════════════════════════════════════╣")
    print(f"║ Версия: {version:<35}║")
    print(f"║ Аккаунт: {username:<34}║")
    print(f"║ Память: {config.get('java_args', '')[5:11]:<35}║")
    print("╚══════════════════════════════════════════════╝")
    
    options = {
        'username': username,
        'uuid': '',
        'token': ''
    }
    
    print("Подготовка к запуску...")
    
    try:
        minecraft_command = minecraft_launcher_lib.command.get_minecraft_command(
            version, MINECRAFT_DIR, options
        )
        
        java_args = config.get("java_args", "").split()
        if java_args:
            minecraft_command = ['java'] + java_args + minecraft_command[1:]
        
        print("Запуск Minecraft...")
        
        subprocess.run(minecraft_command)
        
        print("Minecraft завершил работу")
        
    except Exception as e:
        print(f"Ошибка запуска: {e}")
        print("Проверьте установку Java и наличие файлов игры")

def show_news():
    news_items = [
        ("https://www.minecraft.net", "Официальный сайт Minecraft"),
        ("https://www.minecraft.net/ru-ru/download", "Скачать Minecraft"),
        ("https://github.com/m1r0tv0rets/cobalt_launcher", "Репозиторий Cobalt Launcher"),
        ("https://t.me/tl_chat_ru/687311", "Поддержка Cobalt Launcher"),
    ]
    
    print("╔══════════════════════════════════════════════╗")
    print("║           ПОЛЕЗНЫЕ ССЫЛКИ                    ║")
    print("╚══════════════════════════════════════════════╝")
    
    for url, description in news_items:
        print(f"\n{url}")
        print(f"   {description}")
        print(f"   [Нажмите Enter чтобы открыть ссылку]")
        
        choice = input("   Открыть? (y/n): ").lower()
        if choice == 'y':
            open_url(url)

def create_backup():
    desktop = Path.home() / "Desktop"
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = desktop / f"minecraft_backup_{timestamp}.zip"
    
    folders_to_backup = ["saves", "resourcepacks", "config", "shaderpacks", "schematics"]
    
    print("Создание резервной копии...")
    
    try:
        with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            total_files = 0
            for folder in folders_to_backup:
                folder_path = os.path.join(MINECRAFT_DIR, folder)
                if os.path.exists(folder_path):
                    for root, dirs, files in os.walk(folder_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, MINECRAFT_DIR)
                            zipf.write(file_path, arcname)
                            total_files += 1
        
        print(f"Резервная копия создана!")
        print(f"Файл: {backup_file}")
        print(f"Файлов сохранено: {total_files}")
        
    except Exception as e:
        print(f"Ошибка создания бэкапа: {e}")

def open_minecraft_folder():
    try:
        if platform.system() == "Windows":
            os.startfile(MINECRAFT_DIR)
        elif platform.system() == "Darwin":
            subprocess.run(["open", MINECRAFT_DIR])
        else:
            subprocess.run(["xdg-open", MINECRAFT_DIR])
        print(f"Папка Minecraft открыта: {MINECRAFT_DIR}")
    except Exception as e:
        print(f"Ошибка открытия папки: {e}")

def copy_latest_log():
    logs_dir = os.path.join(MINECRAFT_DIR, "logs")
    
    if not os.path.exists(logs_dir):
        print("Папка logs не найдена")
        return
    
    log_files = [f for f in os.listdir(logs_dir) if f.endswith('.log') or f.endswith('.txt')]
    
    if not log_files:
        print("Лог-файлы не найдены")
        return
    
    latest_log = max(log_files, key=lambda f: os.path.getmtime(os.path.join(logs_dir, f)))
    source_path = os.path.join(logs_dir, latest_log)
    desktop = Path.home() / "Desktop"
    dest_path = desktop / f"minecraft_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    try:
        shutil.copy2(source_path, dest_path)
        print(f"Лог скопирован на рабочий стол: {dest_path}")
    except Exception as e:
        print(f"Ошибка копирования лога: {e}")

def main():
    print_banner()
    
    config = load_config()
    
    print("Не знаете команды? Введите 'помощь' для списка команд")
    
    while True:
        try:
            user_input = input("\ncobalt> ").strip()
            
            if not user_input:
                continue
            
            parts = user_input.split()
            cmd = parts[0].lower()
            
            if cmd == 'помощь' or cmd == 'help':
                print_help()
            
            elif cmd == 'акк' or cmd == 'accounts':
                manage_accounts_scrollable()
            
            elif cmd == 'вер' or cmd == 'versions':
                list_versions_scrollable()
            
            elif cmd == 'установить' and len(parts) > 1:
                install_version(parts[1])
            
            elif cmd == 'запуск' or cmd == 'launch':
                launch_minecraft()
            
            elif cmd == 'арг' or cmd == 'args':
                set_java_args()
            
            elif cmd == 'память' and len(parts) > 1:
                set_memory(parts[1])
            
            elif cmd == 'новости' or cmd == 'news':
                show_news()
            
            elif cmd == 'заметка' and len(parts) > 1:
                note_text = ' '.join(parts[1:])
                with open(NOTES_FILE, 'a', encoding='utf-8') as f:
                    f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')}: {note_text}\n")
                print("Заметка добавлена!")
            
            elif cmd == 'заметки' or cmd == 'notes':
                if os.path.exists(NOTES_FILE):
                    print("╔══════════════════════════════════════════════╗")
                    print("║              ЗАМЕТКИ                         ║")
                    print("╚══════════════════════════════════════════════╝")
                    with open(NOTES_FILE, 'r', encoding='utf-8') as f:
                        print(f.read())
                else:
                    print("Заметок пока нет")
            
            elif cmd == 'бэкап' or cmd == 'backup':
                create_backup()
            
            elif cmd == 'папка' or cmd == 'folder':
                open_minecraft_folder()
            
            elif cmd == 'лог' or cmd == 'log':
                copy_latest_log()
            
            elif cmd == 'выход' or cmd == 'exit' or cmd == 'quit':
                print("До свидания!")
                break
            
            else:
                print(f"Неизвестная команда: {cmd}")
                print("Введите 'помощь' для списка команд")
        
        except KeyboardInterrupt:
            print("\nВыход из лаунчера...")
            break
        except Exception as e:
            print(f"Ошибка: {e}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        input("Нажмите Enter для выхода...")