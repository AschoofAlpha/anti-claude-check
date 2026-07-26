from .transaction import Transaction

def perform_rollback(transaction_id: str = None):
    # If no ID provided, find the latest transaction
    tx = Transaction(transaction_id)
    manifest = tx.get_rollback_manifest()
    
    if not manifest:
        print("No rollback manifest found.")
        return False
        
    print(f"Rolling back {len(manifest)} actions...")
    from .executors import get_executor
    for action in manifest:
        print(f"Rolling back action {action['action_id']}")
        executor = get_executor(action['action_id'])
        success = executor.rollback(action, transaction_id)
        if success:
            print(f"  [OK] Rolled back {action['action_id']}")
        else:
            print(f"  [FAIL] Failed to roll back {action['action_id']}")
            
    print("Rollback complete.")
    return True
