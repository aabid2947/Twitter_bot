

def load_accounts_list(file_path):
    accounts = []
    with open(file_path, mode='r', encoding='utf-8') as file:
        for line in file:
            account = line.strip()  # Remove any leading/trailing whitespace
            if account:  # Avoid empty lines
                accounts.append(account)
    return accounts