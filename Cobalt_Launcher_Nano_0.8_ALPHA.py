import os
import sys
import json
import zipfile
import requests
import subprocess
import platform
import shutil
import re
import threading
import time
import webbrowser
import hashlib
from pathlib import Path
from datetime import datetime
import minecraft_launcher_lib
from colored import fg, attr
import tarfile

COLOR_RED = fg('red')
COLOR_GREEN = fg('green')
COLOR_YELLOW = fg('yellow')
COLOR_BLUE = fg('blue')
COLOR_MAGENTA = fg('magenta')
COLOR_CYAN = fg('cyan')
COLOR_RESET = attr('reset')

LAUNCHER_DATA_DIR = str(Path.home() / ".cobalt_launcher_nano_files")
CONFIG_FILE = os.path.join(LAUNCHER_DATA_DIR, "config.json")
NOTES_FILE = os.path.join(LAUNCHER_DATA_DIR, "notes.txt")
ACCOUNTS_FILE = os.path.join(LAUNCHER_DATA_DIR, "launcher_profiles.json")
JAVA_DIR = os.path.join(LAUNCHER_DATA_DIR, "java")
MINECRAFT_DIR = os.path.join(LAUNCHER_DATA_DIR, "minecraft")

os.makedirs(LAUNCHER_DATA_DIR, exist_ok=True)
os.makedirs(JAVA_DIR, exist_ok=True)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if "separate_version_dirs" not in config:
                    config["separate_version_dirs"] = False
                if "java_path" not in config:
                    config["java_path"] = None
                if "java_version" not in config:
                    config["java_version"] = "17"
                return config
        except json.JSONDecodeError:
            return {"java_args": "-Xmx2G -Xms1G", "selected_version": None, "current_account": None, "separate_version_dirs": False, "java_path": None, "java_version": "17"}
    return {"java_args": "-Xmx2G -Xms1G", "selected_version": None, "current_account": None, "separate_version_dirs": False, "java_path": None, "java_version": "17"}

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
    account_id = max([acc["id"] for acc in accounts], default=0) + 1
    account = {
        "id": account_id,
        "username": username,
        "type": "offline",
        "created_at": datetime.now().isoformat()
    }
    accounts.append(account)
    save_accounts(accounts)
    return account

def add_ely_account(username, email, password):
    print(f"{COLOR_YELLOW}Аутентификация через Ely.by...{COLOR_RESET}")
    auth_url = f"https://ely.by/account/session"
    
    session = requests.Session()
    
    try:
        auth_data = {
            "email": email,
            "password": password,
            "remember": "true"
        }
        
        response = session.post(auth_url, data=auth_data)
        
        if response.status_code == 200:
            accounts = load_accounts()
            account_id = max([acc["id"] for acc in accounts], default=0) + 1
            
            account = {
                "id": account_id,
                "username": username,
                "type": "ely",
                "email": email,
                "session_token": session.cookies.get_dict(),
                "created_at": datetime.now().isoformat()
            }
            
            accounts.append(account)
            save_accounts(accounts)
            
            print(f"{COLOR_GREEN}Аккаунт Ely.by '{username}' успешно добавлен!{COLOR_RESET}")
            return account
        else:
            print(f"{COLOR_RED}Ошибка аутентификации: Неверный email или пароль{COLOR_RESET}")
            return None
            
    except Exception as e:
        print(f"{COLOR_RED}Ошибка подключения к Ely.by: {e}{COLOR_RESET}")
        return None

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

def input_yes_no(prompt):
    while True:
        response = input(prompt).lower()
        if response in ['да', 'д', 'y', 'yes']:
            return True
        elif response in ['нет', 'н', 'n', 'no']:
            return False
        else:
            print(f"{COLOR_RED}Пожалуйста, ответьте 'да' или 'нет'{COLOR_RESET}")

class ScrollableList:
    def __init__(self, items, page_size=10):
        self.items = items
        self.page_size = page_size
        self.current_page = 0
    
    def display_page(self):
        start_idx = self.current_page * self.page_size
        end_idx = start_idx + self.page_size
        page_items = self.items[start_idx:end_idx]
        
        total_pages = (len(self.items) + self.page_size - 1) // self.page_size if self.items else 1
        print(f"{COLOR_CYAN}Страница {self.current_page + 1}/{total_pages}{COLOR_RESET}")
        print(f"{COLOR_BLUE}──────────────────────────────────{COLOR_RESET}")
        
        if not page_items:
            print(f"{COLOR_YELLOW}Нет элементов для отображения{COLOR_RESET}")
        else:
            for i, item in enumerate(page_items, start=1):
                print(f"{COLOR_YELLOW}{start_idx + i:3}.{COLOR_RESET} {item}")
        
        print(f"{COLOR_BLUE}──────────────────────────────────{COLOR_RESET}")
    
    def navigate(self):
        if not self.items:
            print(f"{COLOR_YELLOW}Список пуст{COLOR_RESET}")
            return None
        
        while True:
            self.display_page()
            print(f"\n{COLOR_GREEN}Команды:{COLOR_RESET}")
            print(f"{COLOR_CYAN}с{COLOR_RESET} - следующая страница")
            print(f"{COLOR_CYAN}п{COLOR_RESET} - предыдущая страница")
            print(f"{COLOR_CYAN}число{COLOR_RESET} - выбрать элемент")
            print(f"{COLOR_CYAN}в{COLOR_RESET} - выйти")
            
            choice = input(f"{COLOR_YELLOW}Выберите: {COLOR_RESET}").lower()
            
            if choice == 'с':
                if (self.current_page + 1) * self.page_size < len(self.items):
                    self.current_page += 1
                else:
                    print(f"{COLOR_RED}Это последняя страница{COLOR_RESET}")
            elif choice == 'п':
                if self.current_page > 0:
                    self.current_page -= 1
                else:
                    print(f"{COLOR_RED}Это первая страница{COLOR_RESET}")
            elif choice == 'в':
                return None
            elif choice.isdigit():
                idx = int(choice) - 1
                actual_idx = self.current_page * self.page_size + idx
                if 0 <= actual_idx < len(self.items):
                    return actual_idx
                else:
                    print(f"{COLOR_RED}Неверный номер{COLOR_RESET}")
            else:
                print(f"{COLOR_RED}Неверная команда{COLOR_RESET}")

def print_banner():
    banner = f"""
{COLOR_CYAN}Cobalt Launcher Nano:{COLOR_RESET}
{COLOR_CYAN}Версия: {COLOR_RED}0.8 ALPHA НЕСТАБИЛЬНАЯ{COLOR_RESET}
{COLOR_CYAN}Автор: {COLOR_GREEN}M1rotvorets{COLOR_RESET}
{COLOR_CYAN}Помощники: {COLOR_YELLOW}WaterBucket, Nosok{COLOR_RESET}
{COLOR_CYAN}Репозиторий: {COLOR_BLUE}https://github.com/m1r0tv0rets/Cobalt_Launcher_Nano{COLOR_RESET}
    """
    print(banner)

def print_help():
    help_text = f"""
{COLOR_CYAN}ДОСТУПНЫЕ КОМАНДЫ:{COLOR_RESET}
{COLOR_GREEN}акк{COLOR_RESET}         - Управление аккаунтами
{COLOR_GREEN}альфа{COLOR_RESET}       - Показать альфа версии
{COLOR_GREEN}бета{COLOR_RESET}        - Показать бета версии
{COLOR_GREEN}снапшоты{COLOR_RESET}    - Показать снапшоты
{COLOR_GREEN}релизы{COLOR_RESET}      - Показать релизные версии
{COLOR_GREEN}установить{COLOR_RESET}  - Установить версию
{COLOR_GREEN}запуск{COLOR_RESET}      - Запустить Minecraft
{COLOR_GREEN}арг{COLOR_RESET}         - Настройка аргументов Java
{COLOR_GREEN}память{COLOR_RESET}      - Установить объем памяти (например: 'память 4')
{COLOR_GREEN}моды{COLOR_RESET}        - Открыть папку модов
{COLOR_GREEN}ресурспак{COLOR_RESET}   - Открыть папку ресурспаков
{COLOR_GREEN}миры{COLOR_RESET}        - Открыть папку миров
{COLOR_GREEN}конфиги{COLOR_RESET}     - Открыть папку конфигов
{COLOR_GREEN}схемы{COLOR_RESET}       - Открыть папку схем
{COLOR_GREEN}инфо{COLOR_RESET}        - Полезная информация
{COLOR_GREEN}заметка{COLOR_RESET}     - Добавить заметку
{COLOR_GREEN}заметки{COLOR_RESET}     - Показать все заметки
{COLOR_GREEN}бэкап{COLOR_RESET}       - Создать резервную копию
{COLOR_GREEN}папка{COLOR_RESET}       - Открыть папку Minecraft
{COLOR_GREEN}лог{COLOR_RESET}         - Скопировать последний лог на рабочий стол
{COLOR_GREEN}джава{COLOR_RESET}       - Установить путь к Java
{COLOR_GREEN}установить джава{COLOR_RESET} - Скачать и установить Java
{COLOR_GREEN}краш{COLOR_RESET}        - Скопировать краш-репорты на рабочий стол
{COLOR_GREEN}отдельные папки{COLOR_RESET} - Включить/выключить отдельные папки для версий
{COLOR_GREEN}модлоадеры{COLOR_RESET} - Установка версий с Forge/Fabric
    """
    print(help_text)

def manage_accounts_scrollable():
    accounts = load_accounts()
    config = load_config()
    
    if not accounts:
        print(f"{COLOR_YELLOW}Аккаунты не найдены{COLOR_RESET}")
        print(f"{COLOR_GREEN}Выберите тип аккаунта:{COLOR_RESET}")
        print(f"{COLOR_YELLOW}1.{COLOR_RESET} Оффлайн аккаунт")
        print(f"{COLOR_YELLOW}2.{COLOR_RESET} Ely.by аккаунт")
        
        choice = input(f"{COLOR_YELLOW}Выберите тип: {COLOR_RESET}")
        
        if choice == '1':
            username = input("Введите имя пользователя: ")
            if username:
                account = add_offline_account(username)
                config["current_account"] = account["id"]
                save_config(config)
                print(f"{COLOR_GREEN}Аккаунт '{username}' добавлен!{COLOR_RESET}")
        elif choice == '2':
            username = input("Введите имя пользователя для отображения: ")
            email = input("Введите email от Ely.by: ")
            password = input("Введите пароль от Ely.by: ")
            if username and email and password:
                account = add_ely_account(username, email, password)
                if account:
                    config["current_account"] = account["id"]
                    save_config(config)
        return
    
    while True:
        print(f"\n{COLOR_CYAN}УПРАВЛЕНИЕ АККАУНТАМИ{COLOR_RESET}")
        print(f"{COLOR_BLUE}──────────────────────────────────{COLOR_RESET}")
        
        for acc in accounts:
            status = f"{COLOR_GREEN}✓{COLOR_RESET}" if config.get("current_account") == acc["id"] else " "
            print(f"{status} ID: {acc['id']} | {acc['username']} ({acc['type']})")
        
        print(f"{COLOR_BLUE}──────────────────────────────────{COLOR_RESET}")
        print(f"{COLOR_GREEN}Выберите действие:{COLOR_RESET}")
        print(f"{COLOR_YELLOW}1.{COLOR_RESET} Добавить оффлайн аккаунт")
        print(f"{COLOR_YELLOW}2.{COLOR_RESET} Добавить Ely.by аккаунт")
        print(f"{COLOR_YELLOW}3.{COLOR_RESET} Удалить аккаунт")
        print(f"{COLOR_YELLOW}4.{COLOR_RESET} Выбрать текущий аккаунт")
        print(f"{COLOR_YELLOW}5.{COLOR_RESET} Назад")
        
        choice = input(f"{COLOR_YELLOW}Выберите: {COLOR_RESET}")
        
        if choice == '1':
            username = input("Введите имя пользователя: ")
            if username:
                account = add_offline_account(username)
                print(f"{COLOR_GREEN}Аккаунт '{username}' добавлен с ID {account['id']}!{COLOR_RESET}")
        
        elif choice == '2':
            username = input("Введите имя пользователя для отображения: ")
            email = input("Введите email от Ely.by: ")
            password = input("Введите пароль от Ely.by: ")
            if username and email and password:
                account = add_ely_account(username, email, password)
                if account:
                    print(f"{COLOR_GREEN}Аккаунт Ely.by '{username}' добавлен!{COLOR_RESET}")
        
        elif choice == '3':
            acc_id = input("Введите ID аккаунта для удаления: ")
            if acc_id.isdigit():
                if delete_account(int(acc_id)):
                    print(f"{COLOR_GREEN}Аккаунт удален!{COLOR_RESET}")
                else:
                    print(f"{COLOR_RED}Аккаунт не найден!{COLOR_RESET}")
        
        elif choice == '4':
            acc_id = input("Введите ID аккаунта для выбора: ")
            if acc_id.isdigit():
                acc = get_account_by_id(int(acc_id))
                if acc:
                    config["current_account"] = acc["id"]
                    save_config(config)
                    print(f"{COLOR_GREEN}Текущий аккаунт: {acc['username']}{COLOR_RESET}")
                else:
                    print(f"{COLOR_RED}Аккаунт не найден!{COLOR_RESET}")
        
        elif choice == '5':
            break
        else:
            print(f"{COLOR_RED}Неверный выбор!{COLOR_RESET}")

def list_versions_by_type(version_type):
    print(f"{COLOR_CYAN}Получение списка версий...{COLOR_RESET}")
    
    try:
        versions = minecraft_launcher_lib.utils.get_available_versions(MINECRAFT_DIR)
        filtered_versions = []
        
        for v in versions:
            if version_type == "alpha" and v['type'] == 'old_alpha':
                filtered_versions.append(v)
            elif version_type == "beta" and v['type'] == 'old_beta':
                filtered_versions.append(v)
            elif version_type == "snapshot" and v['type'] == 'snapshot':
                filtered_versions.append(v)
            elif version_type == "release" and v['type'] == 'release':
                filtered_versions.append(v)
        
        if not filtered_versions:
            print(f"{COLOR_YELLOW}Версий данного типа не найдено{COLOR_RESET}")
            return
        
        version_list = [f"{v['id']} ({v['type']})" for v in filtered_versions]
        scroll_list = ScrollableList(version_list[::-1], page_size=15)
        
        type_names = {
            "alpha": "АЛЬФА ВЕРСИИ",
            "beta": "БЕТА ВЕРСИИ",
            "snapshot": "СНАПШОТЫ",
            "release": "РЕЛИЗНЫЕ ВЕРСИИ"
        }
        
        print(f"{COLOR_CYAN}{type_names[version_type]}{COLOR_RESET}")
        
        selected_idx = scroll_list.navigate()
        if selected_idx is not None:
            selected_version = filtered_versions[len(filtered_versions)-1-selected_idx]['id']
            print(f"\n{COLOR_GREEN}Выбрана версия: {selected_version}{COLOR_RESET}")
            
            if input_yes_no("Установить эту версию? (да/нет): "):
                install_version(selected_version)
    
    except Exception as e:
        print(f"{COLOR_RED}Ошибка получения списка версий: {e}{COLOR_RESET}")

def get_minecraft_dir_for_version(version):
    config = load_config()
    if config.get("separate_version_dirs", False):
        return str(Path.home() / f".minecraft_{version}")
    return MINECRAFT_DIR

def install_version(version):
    print(f"{COLOR_CYAN}Установка версии {version}...{COLOR_RESET}")
    
    try:
        minecraft_dir = get_minecraft_dir_for_version(version)
        minecraft_launcher_lib.install.install_minecraft_version(version, minecraft_dir)
        
        config = load_config()
        config["selected_version"] = version
        save_config(config)
        
        print(f"{COLOR_GREEN}Версия {version} успешно установлена!{COLOR_RESET}")
        
    except Exception as e:
        print(f"{COLOR_RED}Ошибка установки: {e}{COLOR_RESET}")

def install_version_with_modloader():
    print(f"{COLOR_CYAN}Установка версии с модлоадером{COLOR_RESET}")
    
    print(f"{COLOR_GREEN}Выберите модлоадер:{COLOR_RESET}")
    print(f"{COLOR_YELLOW}1.{COLOR_RESET} Forge")
    print(f"{COLOR_YELLOW}2.{COLOR_RESET} Fabric")
    print(f"{COLOR_YELLOW}3.{COLOR_RESET} Quilt")
    print(f"{COLOR_YELLOW}4.{COLOR_RESET} NeoForge")
    
    loader_choice = input(f"{COLOR_YELLOW}Выберите модлоадер: {COLOR_RESET}")
    
    if loader_choice not in ['1', '2', '3', '4']:
        print(f"{COLOR_RED}Неверный выбор{COLOR_RESET}")
        return
    
    version = input(f"{COLOR_YELLOW}Введите версию Minecraft (например, 1.20.1): {COLOR_RESET}")
    
    if not version:
        print(f"{COLOR_RED}Версия не указана{COLOR_RESET}")
        return
    
    try:
        minecraft_dir = get_minecraft_dir_for_version(version)
        
        if loader_choice == '1':
            print(f"{COLOR_CYAN}Установка Forge для {version}...{COLOR_RESET}")
            
            try:
                forge_versions = minecraft_launcher_lib.forge.list_forge_versions()
                
                filtered_forge = []
                for forge_ver in forge_versions:
                    if version in forge_ver:
                        filtered_forge.append(forge_ver)
                
                if not filtered_forge:
                    print(f"{COLOR_RED}Forge для версии {version} не найден{COLOR_RESET}")
                    return
                
                print(f"{COLOR_GREEN}Доступные версии Forge:{COLOR_RESET}")
                for i, forge_ver in enumerate(filtered_forge[:10], 1):
                    print(f"{COLOR_YELLOW}{i}.{COLOR_RESET} {forge_ver}")
                
                forge_choice = input(f"{COLOR_YELLOW}Выберите версию Forge (1-{min(10, len(filtered_forge))}): {COLOR_RESET}")
                
                if forge_choice.isdigit():
                    idx = int(forge_choice) - 1
                    if 0 <= idx < len(filtered_forge):
                        forge_version = filtered_forge[idx]
                        print(f"{COLOR_CYAN}Установка {forge_version}...{COLOR_RESET}")
                        minecraft_launcher_lib.forge.install_forge_version(forge_version, minecraft_dir)
                        config = load_config()
                        config["selected_version"] = forge_version
                        save_config(config)
                        print(f"{COLOR_GREEN}Forge {forge_version} успешно установлен!{COLOR_RESET}")
            except Exception as e:
                print(f"{COLOR_RED}Ошибка установки Forge: {e}{COLOR_RESET}")
                return
        
        elif loader_choice == '2':
            print(f"{COLOR_CYAN}Установка Fabric для {version}...{COLOR_RESET}")
            
            try:
                minecraft_launcher_lib.fabric.install_fabric(version, minecraft_dir)
                fabric_version_id = f"fabric-loader-0.15.11-{version}"
                
                config = load_config()
                config["selected_version"] = fabric_version_id
                save_config(config)
                
                print(f"{COLOR_GREEN}Fabric для Minecraft {version} успешно установлен!{COLOR_RESET}")
            except Exception as e:
                print(f"{COLOR_RED}Ошибка установки Fabric: {e}{COLOR_RESET}")
                return
        
        elif loader_choice == '3':
            print(f"{COLOR_CYAN}Установка Quilt для {version}...{COLOR_RESET}")
            
            try:
                response = requests.get("https://meta.quiltmc.org/v3/versions/loader")
                if response.status_code == 200:
                    quilt_versions = response.json()
                    
                    latest_loader = None
                    for item in quilt_versions:
                        if isinstance(item, dict) and 'loader' in item:
                            loader_data = item['loader']
                            if isinstance(loader_data, dict) and 'version' in loader_data:
                                latest_loader = loader_data['version']
                                break
                    
                    if latest_loader:
                        minecraft_launcher_lib.fabric.install_fabric(version, minecraft_dir, latest_loader)
                        quilt_version_id = f"quilt-loader-{latest_loader}-{version}"
                        
                        config = load_config()
                        config["selected_version"] = quilt_version_id
                        save_config(config)
                        
                        print(f"{COLOR_GREEN}Quilt {latest_loader} для Minecraft {version} успешно установлен!{COLOR_RESET}")
                    else:
                        print(f"{COLOR_RED}Не удалось получить версию Quilt Loader{COLOR_RESET}")
                        return
                else:
                    print(f"{COLOR_RED}Не удалось получить версии Quilt{COLOR_RESET}")
                    return
            except Exception as e:
                print(f"{COLOR_RED}Ошибка установки Quilt: {e}{COLOR_RESET}")
                return
        
        elif loader_choice == '4':
            print(f"{COLOR_CYAN}Установка NeoForge для {version}...{COLOR_RESET}")
            
            try:
                response = requests.get("https://maven.neoforged.net/api/maven/versions/releases/net/neoforged/neoforge")
                if response.status_code == 200:
                    neoforge_data = response.json()
                    
                    if 'versions' in neoforge_data:
                        filtered_neoforge = []
                        for v in neoforge_data['versions']:
                            if version in v:
                                filtered_neoforge.append(v)
                        
                        if filtered_neoforge:
                            latest_neoforge = filtered_neoforge[-1]
                            print(f"{COLOR_CYAN}Установка NeoForge {latest_neoforge}...{COLOR_RESET}")
                            
                            minecraft_launcher_lib.forge.install_forge_version(latest_neoforge, minecraft_dir)
                            
                            config = load_config()
                            config["selected_version"] = latest_neoforge
                            save_config(config)
                            
                            print(f"{COLOR_GREEN}NeoForge {latest_neoforge} успешно установлен!{COLOR_RESET}")
                        else:
                            print(f"{COLOR_RED}NeoForge для версии {version} не найден{COLOR_RESET}")
                            return
                    else:
                        print(f"{COLOR_RED}Не удалось получить версии NeoForge{COLOR_RESET}")
                        return
                else:
                    print(f"{COLOR_RED}Ошибка получения версий NeoForge{COLOR_RESET}")
                    return
            except Exception as e:
                print(f"{COLOR_RED}Ошибка установки NeoForge: {e}{COLOR_RESET}")
                return
    
    except Exception as e:
        print(f"{COLOR_RED}Ошибка установки модлоадера: {e}{COLOR_RESET}")

def set_java_args():
    config = load_config()
    current_args = config.get("java_args", "-Xmx2G -Xms1G")
    
    print(f"\n{COLOR_CYAN}Текущие аргументы Java: {current_args}{COLOR_RESET}")
    print(f"{COLOR_YELLOW}Примеры:{COLOR_RESET}")
    print(f"{COLOR_GREEN}  -Xmx4G -Xms2G{COLOR_RESET} - 4GB максимум, 2GB минимум")
    print(f"{COLOR_GREEN}  -Xmx8G -Xms4G -XX:+UseG1GC{COLOR_RESET} - с оптимизацией G1GC")
    
    new_args = input(f"\n{COLOR_YELLOW}Введите новые аргументы (Enter для отмены): {COLOR_RESET}")
    
    if new_args:
        config["java_args"] = new_args
        save_config(config)
        print(f"{COLOR_GREEN}Аргументы обновлены!{COLOR_RESET}")

def set_memory(gb):
    if not gb.isdigit():
        print(f"{COLOR_RED}Укажите количество гигабайт числом{COLOR_RESET}")
        return
    
    gb_int = int(gb)
    if gb_int < 1 or gb_int > 32:
        print(f"{COLOR_RED}Укажите значение от 1 до 32 GB{COLOR_RESET}")
        return
    
    config = load_config()
    current_args = config.get("java_args", "")
    
    new_args = re.sub(r"-Xmx\d+G", "", current_args)
    new_args = re.sub(r"-Xms\d+G", "", new_args)
    new_args = re.sub(r"\s+", " ", new_args).strip()
    
    memory_args = f"-Xmx{gb}G -Xms{gb}G"
    if new_args:
        new_args = f"{memory_args} {new_args}"
    else:
        new_args = memory_args
    
    config["java_args"] = new_args
    save_config(config)
    print(f"{COLOR_GREEN}Память установлена на {gb}GB{COLOR_RESET}")

minecraft_process = None

def launch_minecraft():
    global minecraft_process
    
    config = load_config()
    
    if not config.get("selected_version"):
        print(f"{COLOR_RED}Сначала установите версию Minecraft!{COLOR_RESET}")
        print(f"{COLOR_YELLOW}Используйте команду 'установить' для выбора версии{COLOR_RESET}")
        return
    
    accounts = load_accounts()
    current_account_id = config.get("current_account")
    
    if not current_account_id or not any(a["id"] == current_account_id for a in accounts):
        print(f"{COLOR_RED}Сначала настройте аккаунт!{COLOR_RESET}")
        print(f"{COLOR_YELLOW}Используйте команду 'акк' для управления аккаунтами{COLOR_RESET}")
        return
    
    account = next((a for a in accounts if a["id"] == current_account_id), None)
    if not account:
        print(f"{COLOR_RED}Аккаунт не найден!{COLOR_RESET}")
        return
    
    version = config["selected_version"]
    username = account["username"]
    minecraft_dir = get_minecraft_dir_for_version(version)
    
    java_path = config.get("java_path")
    if java_path and os.path.exists(java_path):
        try:
            result = subprocess.run([java_path, "-version"], capture_output=True, text=True, shell=True)
            java_version_output = result.stderr or result.stdout
            
            version_match = re.search(r'version "(\d+)', java_version_output)
            if version_match:
                java_version = int(version_match.group(1))
                print(f"{COLOR_GREEN}Найдена Java версии: {java_version}{COLOR_RESET}")
                
                mc_version_match = re.match(r'(\d+)\.(\d+)\.(\d+)', version)
                if mc_version_match:
                    major_version = int(mc_version_match.group(2))
                    if major_version >= 17:
                        required_java = 17
                    elif major_version >= 12:
                        required_java = 11
                    else:
                        required_java = 8
                    
                    if java_version < required_java:
                        print(f"{COLOR_RED}ВНИМАНИЕ: Для Minecraft {version} требуется Java {required_java} или выше!{COLOR_RESET}")
                        print(f"{COLOR_RED}Текущая Java: {java_version}{COLOR_RESET}")
                        print(f"{COLOR_YELLOW}Используйте команду 'установить джава' для установки подходящей версии Java{COLOR_RESET}")
                        if not input_yes_no("Продолжить запуск? (да/нет): "):
                            return
            else:
                print(f"{COLOR_YELLOW}Не удалось определить версию Java{COLOR_RESET}")
        except Exception as e:
            print(f"{COLOR_YELLOW}Не удалось проверить версию Java: {e}{COLOR_RESET}")
    else:
        print(f"{COLOR_YELLOW}Путь к Java не установлен, будет использована системная Java{COLOR_RESET}")
    
    print(f"{COLOR_CYAN}ЗАПУСК MINECRAFT{COLOR_RESET}")
    print(f"{COLOR_BLUE}──────────────────────────────────{COLOR_RESET}")
    print(f"{COLOR_GREEN}Версия:{COLOR_RESET} {version}")
    print(f"{COLOR_GREEN}Аккаунт:{COLOR_RESET} {username}")
    
    memory_match = re.search(r'-Xmx(\d+)G', config.get("java_args", ""))
    if memory_match:
        memory_gb = memory_match.group(1)
        print(f"{COLOR_GREEN}Память:{COLOR_RESET} {memory_gb}GB")
    else:
        print(f"{COLOR_GREEN}Память:{COLOR_RESET} 2GB (по умолчанию)")
    
    print(f"{COLOR_GREEN}Папка:{COLOR_RESET} {minecraft_dir}")
    print(f"{COLOR_BLUE}──────────────────────────────────{COLOR_RESET}")
    
    options = {
        'username': username,
        'uuid': '',
        'token': ''
    }
    
    if account.get('type') == 'ely':
        options['token'] = 'ely_token'
    
    print(f"{COLOR_CYAN}Подготовка к запуску...{COLOR_RESET}")
    
    try:
        minecraft_command = minecraft_launcher_lib.command.get_minecraft_command(
            version, minecraft_dir, options
        )
        
        java_args = config.get("java_args", "").split()
        
        java_executable = 'java'
        if java_path:
            java_executable = java_path
        elif platform.system() == "Linux":
            java_executable = shutil.which("java") or "java"
        
        minecraft_command = [java_executable] + java_args + minecraft_command[1:]
        
        print(f"{COLOR_GREEN}Запуск Minecraft...{COLOR_RESET}")
        
        minecraft_process = subprocess.Popen(minecraft_command)
        
        minecraft_process.wait()
        
        print(f"{COLOR_GREEN}Minecraft завершил работу{COLOR_RESET}")
        
    except Exception as e:
        print(f"{COLOR_RED}Ошибка запуска: {e}{COLOR_RESET}")
        print(f"{COLOR_YELLOW}Проверьте установку Java и наличие файлов игры{COLOR_RESET}")
        print(f"{COLOR_YELLOW}Попробуйте установить Java 17 командой 'установить джава'{COLOR_RESET}")

def show_info():
    print(f"{COLOR_CYAN}Последние новости Minecraft{COLOR_RESET}")
    print(f"{COLOR_BLUE}- https://t.me/nerkinboat{COLOR_RESET}")
    print(f"{COLOR_BLUE}- https://www.youtube.com/@Nerkin/{COLOR_RESET}")
    print(f"{COLOR_CYAN}- Реклама:{COLOR_RESET}")
    print(f"{COLOR_BLUE}- https://t.me/minecraft_cubach Айпи: cubach.com{COLOR_RESET}")
    print(f"{COLOR_CYAN}- Сервер ванилла+ (ванилла с плагинами) Есть боссы, напитки, кастомные вещи, дружелюбное комьюнити.{COLOR_RESET}")
    print(f"{COLOR_BLUE}- https://t.me/playdacha Айпи: playdacha.ru{COLOR_RESET}")
    print(f"{COLOR_CYAN}- Ванильнный сервер майнкрафт. Есть приваты и команда /home. Маленькое и дружелюбное комьюнити.{COLOR_RESET}")

def create_backup():
    desktop = Path.home() / "Desktop"
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = desktop / f"minecraft_backup_{timestamp}.zip"
    
    folders_to_backup = ["saves", "resourcepacks", "config", "shaderpacks", "schematics", "mods"]
    
    print(f"{COLOR_CYAN}Создание резервной копии...{COLOR_RESET}")
    
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
        
        print(f"{COLOR_GREEN}Резервная копия создана!{COLOR_RESET}")
        print(f"{COLOR_CYAN}Файл: {backup_file}{COLOR_RESET}")
        print(f"{COLOR_CYAN}Файлов сохранено: {total_files}{COLOR_RESET}")
        
    except Exception as e:
        print(f"{COLOR_RED}Ошибка создания бэкапа: {e}{COLOR_RESET}")

def open_minecraft_folder():
    try:
        if platform.system() == "Windows":
            os.startfile(MINECRAFT_DIR)
        else:
            subprocess.run(["xdg-open", MINECRAFT_DIR], check=True)
        print(f"{COLOR_GREEN}Папка Minecraft открыта: {MINECRAFT_DIR}{COLOR_RESET}")
    except Exception as e:
        print(f"{COLOR_RED}Ошибка открытия папки: {e}{COLOR_RESET}")

def open_folder(folder_name):
    folder_path = os.path.join(MINECRAFT_DIR, folder_name)
    if not os.path.exists(folder_path):
        print(f"{COLOR_YELLOW}Папка {folder_name} не существует.{COLOR_RESET}")
        if input_yes_no("Создать папку? (да/нет): "):
            os.makedirs(folder_path)
            print(f"{COLOR_GREEN}Папка создана: {folder_path}{COLOR_RESET}")
        else:
            return
    
    try:
        if platform.system() == "Windows":
            os.startfile(folder_path)
        else:
            subprocess.run(["xdg-open", folder_path], check=True)
        print(f"{COLOR_GREEN}Папка {folder_name} открыта: {folder_path}{COLOR_RESET}")
    except Exception as e:
        print(f"{COLOR_RED}Ошибка открытия папки: {e}{COLOR_RESET}")

def copy_latest_log():
    logs_dir = os.path.join(MINECRAFT_DIR, "logs")
    
    if not os.path.exists(logs_dir):
        print(f"{COLOR_YELLOW}Папка logs не найдена{COLOR_RESET}")
        return
    
    log_files = [f for f in os.listdir(logs_dir) if f.endswith('.log') or f.endswith('.txt')]
    
    if not log_files:
        print(f"{COLOR_YELLOW}Лог-файлы не найдены{COLOR_RESET}")
        return
    
    latest_log = max(log_files, key=lambda f: os.path.getmtime(os.path.join(logs_dir, f)))
    source_path = os.path.join(logs_dir, latest_log)
    desktop = Path.home() / "Desktop"
    dest_path = desktop / f"minecraft_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    try:
        shutil.copy2(source_path, dest_path)
        print(f"{COLOR_GREEN}Лог скопирован на рабочий стол: {dest_path}{COLOR_RESET}")
    except Exception as e:
        print(f"{COLOR_RED}Ошибка копирования лога: {e}{COLOR_RESET}")

def set_java_path():
    config = load_config()
    current_path = config.get("java_path", "Не установлен")
    
    print(f"\n{COLOR_CYAN}Текущий путь к Java: {current_path}{COLOR_RESET}")
    print(f"{COLOR_YELLOW}Примеры:{COLOR_RESET}")
    print(f"{COLOR_GREEN}  C:\\Program Files\\Java\\jdk-17\\bin\\java.exe{COLOR_RESET} - Windows")
    print(f"{COLOR_GREEN}  /usr/lib/jvm/java-17-openjdk/bin/java{COLOR_RESET} - Linux")
    
    new_path = input(f"\n{COLOR_YELLOW}Введите новый путь к Java (Enter для сброса): {COLOR_RESET}")
    
    if new_path:
        if os.path.exists(new_path):
            config["java_path"] = new_path
            save_config(config)
            print(f"{COLOR_GREEN}Путь к Java обновлен!{COLOR_RESET}")
            
            try:
                result = subprocess.run([new_path, "-version"], capture_output=True, text=True, shell=True)
                java_version_output = result.stderr or result.stdout
                version_match = re.search(r'version "(\d+)', java_version_output)
                if version_match:
                    java_version = int(version_match.group(1))
                    print(f"{COLOR_GREEN}Версия Java: {java_version}{COLOR_RESET}")
                    config["java_version"] = str(java_version)
                    save_config(config)
            except Exception as e:
                print(f"{COLOR_YELLOW}Не удалось проверить версию Java: {e}{COLOR_RESET}")
        else:
            print(f"{COLOR_RED}Указанный путь не существует!{COLOR_RESET}")
    elif new_path == "" and current_path != "Не установлен":
        config["java_path"] = None
        config["java_version"] = "17"
        save_config(config)
        print(f"{COLOR_GREEN}Путь к Java сброшен, будет использована системная Java.{COLOR_RESET}")

def toggle_separate_dirs():
    config = load_config()
    current = config.get("separate_version_dirs", False)
    config["separate_version_dirs"] = not current
    
    status = "включено" if config["separate_version_dirs"] else "выключено"
    print(f"{COLOR_CYAN}Отдельные папки для версий: {COLOR_GREEN}{status}{COLOR_RESET}")
    
    if config["separate_version_dirs"]:
        print(f"{COLOR_YELLOW}Теперь каждая версия Minecraft будет установлена в отдельную папку.{COLOR_RESET}")
        print(f"{COLOR_YELLOW}Например: .minecraft_1.20.1, .minecraft_1.19.4 и т.д.{COLOR_RESET}")
    else:
        print(f"{COLOR_YELLOW}Все версии Minecraft будут использовать одну папку .minecraft{COLOR_RESET}")
    
    save_config(config)

def install_java():
    print(f"{COLOR_CYAN}Автоматическая установка Java...{COLOR_RESET}")
    
    system = platform.system()
    arch = platform.machine().lower()
    
    if "arm" in arch or "aarch" in arch:
        arch = "arm"
    elif "64" in arch:
        arch = "x64"
    else:
        arch = "x32"
    
    java_versions = {
        "1": {"name": "Java 8", "version": "8"},
        "2": {"name": "Java 11", "version": "11"},
        "3": {"name": "Java 17", "version": "17"},
        "4": {"name": "Java 21", "version": "21"}
    }
    
    print(f"{COLOR_YELLOW}Выберите версию Java для установки:{COLOR_RESET}")
    print(f"{COLOR_RED}ВНИМАНИЕ: Для Minecraft 1.17+ требуется Java 17 или выше!{COLOR_RESET}")
    
    for key, value in java_versions.items():
        print(f"{COLOR_CYAN}{key}.{COLOR_RESET} {value['name']}")
    
    choice = input(f"{COLOR_YELLOW}Ваш выбор (1-4, рекомендуется 3 для Java 17): {COLOR_RESET}")
    
    if choice not in java_versions:
        print(f"{COLOR_RED}Неверный выбор{COLOR_RESET}")
        return
    
    java_version = java_versions[choice]["version"]
    
    print(f"{COLOR_CYAN}Определение вашей системы...{COLOR_RESET}")
    print(f"{COLOR_GREEN}Система: {system}, Архитектура: {arch}{COLOR_RESET}")
    
    base_url = "https://github.com/adoptium/temurin"
    
    if system == "Windows":
        if arch == "x64":
            if java_version == "8":
                url = f"{base_url}8-binaries/releases/download/jdk8u412-b07/OpenJDK8U-jdk_x64_windows_hotspot_8u412b07.zip"
            elif java_version == "11":
                url = f"{base_url}11-binaries/releases/download/jdk-11.0.22%2B7/OpenJDK11U-jdk_x64_windows_hotspot_11.0.22_7.zip"
            elif java_version == "17":
                url = f"{base_url}17-binaries/releases/download/jdk-17.0.10%2B7/OpenJDK17U-jdk_x64_windows_hotspot_17.0.10_7.zip"
            elif java_version == "21":
                url = f"{base_url}21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jdk_x64_windows_hotspot_21.0.2_13.zip"
            ext = "zip"
        else:
            print(f"{COLOR_RED}Архитектура {arch} не поддерживается для Windows{COLOR_RESET}")
            return
    elif system == "Linux":
        if arch == "x64":
            if java_version == "8":
                url = f"{base_url}8-binaries/releases/download/jdk8u412-b07/OpenJDK8U-jdk_x64_linux_hotspot_8u412b07.tar.gz"
            elif java_version == "11":
                url = f"{base_url}11-binaries/releases/download/jdk-11.0.22%2B7/OpenJDK11U-jdk_x64_linux_hotspot_11.0.22_7.tar.gz"
            elif java_version == "17":
                url = f"{base_url}17-binaries/releases/download/jdk-17.0.10%2B7/OpenJDK17U-jdk_x64_linux_hotspot_17.0.10_7.tar.gz"
            elif java_version == "21":
                url = f"{base_url}21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jdk_x64_linux_hotspot_21.0.2_13.tar.gz"
            ext = "tar.gz"
        elif arch == "arm":
            if java_version == "8":
                url = f"{base_url}8-binaries/releases/download/jdk8u412-b07/OpenJDK8U-jdk_aarch64_linux_hotspot_8u412b07.tar.gz"
            elif java_version == "11":
                url = f"{base_url}11-binaries/releases/download/jdk-11.0.22%2B7/OpenJDK11U-jdk_aarch64_linux_hotspot_11.0.22_7.tar.gz"
            elif java_version == "17":
                url = f"{base_url}17-binaries/releases/download/jdk-17.0.10%2B7/OpenJDK17U-jdk_aarch64_linux_hotspot_17.0.10_7.tar.gz"
            elif java_version == "21":
                url = f"{base_url}21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jdk_aarch64_linux_hotspot_21.0.2_13.tar.gz"
            ext = "tar.gz"
        else:
            print(f"{COLOR_RED}Архитектура {arch} не поддерживается для Linux{COLOR_RESET}")
            return
    else:
        print(f"{COLOR_RED}Операционная система {system} не поддерживается{COLOR_RESET}")
        return
    
    java_install_dir = os.path.join(JAVA_DIR, f"java_{java_version}")
    os.makedirs(java_install_dir, exist_ok=True)
    
    download_path = os.path.join(java_install_dir, f"java.{ext}")
    
    print(f"{COLOR_CYAN}Скачивание Java {java_version}...{COLOR_RESET}")
    print(f"{COLOR_YELLOW}URL: {url}{COLOR_RESET}")
    
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(download_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r{COLOR_CYAN}Прогресс: {percent:.1f}% ({downloaded/1024/1024:.1f} MB / {total_size/1024/1024:.1f} MB){COLOR_RESET}", end="")
        
        print(f"\n{COLOR_GREEN}Скачивание завершено{COLOR_RESET}")
        
        print(f"{COLOR_CYAN}Распаковка...{COLOR_RESET}")
        
        if ext == "zip":
            with zipfile.ZipFile(download_path, 'r') as zip_ref:
                zip_ref.extractall(java_install_dir)
        else:
            with tarfile.open(download_path, 'r:gz') as tar_ref:
                tar_ref.extractall(java_install_dir)
        
        os.remove(download_path)
        
        java_exe = "java"
        if system == "Windows":
            for root, dirs, files in os.walk(java_install_dir):
                if "java.exe" in files:
                    java_exe = os.path.join(root, "java.exe")
                    break
            if java_exe == "java":
                for root, dirs, files in os.walk(java_install_dir):
                    if "bin" in dirs:
                        bin_path = os.path.join(root, "bin")
                        if os.path.exists(os.path.join(bin_path, "java.exe")):
                            java_exe = os.path.join(bin_path, "java.exe")
                            break
        else:
            for root, dirs, files in os.walk(java_install_dir):
                if "java" in files and os.access(os.path.join(root, "java"), os.X_OK):
                    java_exe = os.path.join(root, "java")
                    break
            if java_exe == "java":
                for root, dirs, files in os.walk(java_install_dir):
                    if "bin" in dirs:
                        bin_path = os.path.join(root, "bin")
                        if os.path.exists(os.path.join(bin_path, "java")) and os.access(os.path.join(bin_path, "java"), os.X_OK):
                            java_exe = os.path.join(bin_path, "java")
                            break
        
        if os.path.exists(java_exe):
            config = load_config()
            config["java_path"] = java_exe
            config["java_version"] = java_version
            save_config(config)
            
            print(f"{COLOR_GREEN}Java {java_version} успешно установлена!{COLOR_RESET}")
            print(f"{COLOR_CYAN}Путь к Java: {java_exe}{COLOR_RESET}")
            
            if input_yes_no("Проверить установку Java? (да/нет): "):
                try:
                    result = subprocess.run([java_exe, "-version"], capture_output=True, text=True, shell=True)
                    print(f"{COLOR_GREEN}Java версия:{COLOR_RESET}")
                    lines = result.stderr.split('\n') if result.stderr else result.stdout.split('\n')
                    for line in lines[:3]:
                        print(line)
                except Exception as e:
                    print(f"{COLOR_RED}Ошибка проверки Java: {e}{COLOR_RESET}")
        else:
            print(f"{COLOR_YELLOW}Java установлена, но исполняемый файл не найден{COLOR_RESET}")
            print(f"{COLOR_YELLOW}Установите путь к Java вручную командой 'джава'{COLOR_RESET}")
    
    except Exception as e:
        print(f"{COLOR_RED}Ошибка установки Java: {e}{COLOR_RESET}")

def copy_crash_reports():
    crashes_dir = os.path.join(MINECRAFT_DIR, "crashes")
    
    if not os.path.exists(crashes_dir):
        print(f"{COLOR_YELLOW}Папка crashes не найдена{COLOR_RESET}")
        return
    
    crash_files = []
    for root, dirs, files in os.walk(crashes_dir):
        for file in files:
            if file.endswith('.txt') and 'crash' in file.lower():
                crash_files.append(os.path.join(root, file))
    
    if not crash_files:
        print(f"{COLOR_YELLOW}Краш-репорты не найдены{COLOR_RESET}")
        return
    
    desktop = Path.home() / "Desktop"
    crash_folder = desktop / f"minecraft_crash_reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(crash_folder, exist_ok=True)
    
    copied_files = 0
    for crash_file in crash_files:
        try:
            dest_file = os.path.join(crash_folder, os.path.basename(crash_file))
            shutil.copy2(crash_file, dest_file)
            copied_files += 1
        except Exception as e:
            print(f"{COLOR_RED}Ошибка копирования {crash_file}: {e}{COLOR_RESET}")
    
    if copied_files > 0:
        print(f"{COLOR_GREEN}Скопировано {copied_files} краш-репортов в папку: {crash_folder}{COLOR_RESET}")
        
        if platform.system() == "Windows":
            os.startfile(crash_folder)
        else:
            subprocess.run(["xdg-open", crash_folder], check=False)
    else:
        print(f"{COLOR_RED}Не удалось скопировать ни одного краш-репорта{COLOR_RESET}")

def main():
    print_banner()
    
    config = load_config()
    
    print(f"{COLOR_MAGENTA}Не знаете команды? Введите '{COLOR_GREEN}помощь{COLOR_MAGENTA}' для списка команд{COLOR_RESET}")
    
    while True:
        try:
            user_input = input(f"\n{COLOR_CYAN}Введите команду>{COLOR_RESET} ").strip()
            
            if not user_input:
                continue
            
            parts = user_input.split()
            cmd = parts[0].lower()
            
            if cmd == 'помощь' or cmd == 'help':
                print_help()
            
            elif cmd == 'акк' or cmd == 'accounts':
                manage_accounts_scrollable()
            
            elif cmd == 'альфа':
                list_versions_by_type("alpha")
            
            elif cmd == 'бета':
                list_versions_by_type("beta")
            
            elif cmd == 'снапшоты':
                list_versions_by_type("snapshot")
            
            elif cmd == 'релизы':
                list_versions_by_type("release")
            
            elif cmd == 'установить' and len(parts) > 1:
                if parts[1] == 'джава':
                    install_java()
                else:
                    install_version(parts[1])
            
            elif cmd == 'запуск' or cmd == 'launch':
                launch_minecraft()
            
            elif cmd == 'арг' or cmd == 'args':
                set_java_args()
            
            elif cmd == 'память' and len(parts) > 1:
                set_memory(parts[1])
            
            elif cmd == 'моды':
                open_folder("mods")
            
            elif cmd == 'ресурспак':
                open_folder("resourcepacks")
            
            elif cmd == 'миры':
                open_folder("saves")
            
            elif cmd == 'конфиги':
                open_folder("config")
            
            elif cmd == 'схемы':
                open_folder("schematics")
            
            elif cmd == 'инфо':
                show_info()
            
            elif cmd == 'заметка' and len(parts) > 1:
                note_text = ' '.join(parts[1:])
                with open(NOTES_FILE, 'a', encoding='utf-8') as f:
                    f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')}: {note_text}\n")
                print(f"{COLOR_GREEN}Заметка добавлена!{COLOR_RESET}")
            
            elif cmd == 'заметки' or cmd == 'notes':
                if os.path.exists(NOTES_FILE):
                    print(f"{COLOR_CYAN}ЗАМЕТКИ{COLOR_RESET}")
                    with open(NOTES_FILE, 'r', encoding='utf-8') as f:
                        print(f.read())
                else:
                    print(f"{COLOR_YELLOW}Заметок пока нет{COLOR_RESET}")
            
            elif cmd == 'бэкап' or cmd == 'backup':
                create_backup()
            
            elif cmd == 'папка' or cmd == 'folder':
                open_minecraft_folder()
            
            elif cmd == 'лог' or cmd == 'log':
                copy_latest_log()
            
            elif cmd == 'краш' or cmd == 'crash':
                copy_crash_reports()
            
            elif cmd == 'джава':
                set_java_path()
            
            elif user_input.lower() == 'отдельные папки':
                toggle_separate_dirs()
            
            elif cmd == 'модлоадеры' or cmd == 'modloader':
                install_version_with_modloader()
            
            else:
                print(f"{COLOR_RED}Неизвестная команда: {cmd}{COLOR_RESET}")
                print(f"{COLOR_YELLOW}Введите '{COLOR_GREEN}помощь{COLOR_YELLOW}' для списка команд{COLOR_RESET}")
        
        except KeyboardInterrupt:
            print(f"\n{COLOR_CYAN}Выход из лаунчера...{COLOR_RESET}")
            break
        except Exception as e:
            print(f"{COLOR_RED}Ошибка: {e}{COLOR_RESET}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"{COLOR_RED}Критическая ошибка: {e}{COLOR_RESET}")
        input("Нажмите Enter для выхода...")