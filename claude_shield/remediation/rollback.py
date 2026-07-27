from .transaction import Transaction

def perform_rollback(transaction_id: str = None):
    tx = Transaction(transaction_id)
    tx.rollback()
    return True
