"""
Manual test script for thread persistence (two-phase model).
Run this after creating a new chat to verify everything works.

Usage: py test_thread_persistence.py
"""

import sqlite3
from datetime import datetime

def test_thread_persistence():
    print("=" * 60)
    print("THREAD PERSISTENCE TEST")
    print("=" * 60)
    
    conn = sqlite3.connect('chainlit.db')
    cursor = conn.cursor()
    
    # Test 1: Check for complete threads
    print("\n1. COMPLETE THREADS (should have userId AND userIdentifier):")
    cursor.execute("""
        SELECT id, name, userId, userIdentifier, createdAt 
        FROM threads 
        WHERE userId IS NOT NULL AND userIdentifier IS NOT NULL
        ORDER BY createdAt DESC 
        LIMIT 5
    """)
    complete_threads = cursor.fetchall()
    
    if complete_threads:
        for t in complete_threads:
            thread_id = t[0][:8] + "..."
            name = t[1] or "(no name)"
            user_id = t[2][:8] + "..." if t[2] else "NULL"
            user_ident = t[3] or "NULL"
            created = t[4][:19]
            print(f"  [OK] {thread_id} | {name:20} | userId={user_id} | userIdent={user_ident} | {created}")
        print(f"  Total complete threads: {len(complete_threads)}")
    else:
        print("  [WARN] No complete threads found!")
    
    # Test 2: Check for pending threads (may exist temporarily)
    print("\n2. PENDING THREADS (temporary between create_step and update_thread):")
    cursor.execute("""
        SELECT id, name, userId, userIdentifier, createdAt 
        FROM threads 
        WHERE userId IS NULL OR userIdentifier IS NULL
        ORDER BY createdAt DESC
    """)
    pending_threads = cursor.fetchall()
    
    if pending_threads:
        print(f"  [INFO] Found {len(pending_threads)} pending threads (may be transient)")
        for t in pending_threads:
            thread_id = t[0][:8] + "..."
            name = t[1] or "(no name)"
            created = t[4][:19]
            print(f"     - {thread_id} | {name:20} | created={created}")
        print("  NOTE: Pending threads are hidden from sidebar and resume.")
        print("  TIP: Consider cleanup strategy for pending older than 24h.")
    else:
        print("  [OK] No pending threads found")
    
    # Test 3: Check steps per thread
    print("\n3. STEPS PER THREAD (verify data persistence):")
    cursor.execute("""
        SELECT t.id, t.name, COUNT(s.id) as step_count, t.createdAt
        FROM threads t
        LEFT JOIN steps s ON t.id = s.threadId
        WHERE t.userId IS NOT NULL AND t.userIdentifier IS NOT NULL
        GROUP BY t.id, t.name, t.createdAt
        ORDER BY t.createdAt DESC
        LIMIT 5
    """)
    threads_with_steps = cursor.fetchall()
    
    for t in threads_with_steps:
        thread_id = t[0][:8] + "..."
        name = t[1] or "(no name)"
        step_count = t[2]
        created = t[3][:19]
        status = "[OK]" if step_count > 0 else "[WARN]"
        print(f"  {status} {thread_id} | {name:20} | {step_count} steps | {created}")
    
    # Test 4: Latest thread details
    print("\n4. LATEST THREAD (detailed inspection):")
    cursor.execute("""
        SELECT id, name, userId, userIdentifier, tags, metadata, createdAt
        FROM threads 
        WHERE userId IS NOT NULL AND userIdentifier IS NOT NULL
        ORDER BY createdAt DESC 
        LIMIT 1
    """)
    latest = cursor.fetchone()
    
    if latest:
        print(f"  ID: {latest[0]}")
        print(f"  Name: {latest[1] or '(no name)'}")
        print(f"  UserId: {latest[2]}")
        print(f"  UserIdentifier: {latest[3]}")
        print(f"  Tags: {latest[4]}")
        print(f"  Metadata: {latest[5][:100]}..." if len(latest[5]) > 100 else f"  Metadata: {latest[5]}")
        print(f"  Created: {latest[6]}")
        
        # Check steps for this thread
        cursor.execute("SELECT COUNT(*) FROM steps WHERE threadId = ?", (latest[0],))
        step_count = cursor.fetchone()[0]
        print(f"  Steps: {step_count}")
        
        if step_count == 0:
            print("  [WARN] Thread has no steps - this might indicate data loss!")
    else:
        print("  [WARN] No threads found")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    cursor.execute("SELECT COUNT(*) FROM threads")
    total_threads = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM threads WHERE userId IS NOT NULL AND userIdentifier IS NOT NULL")
    complete_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM threads WHERE userId IS NULL OR userIdentifier IS NULL")
    pending_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM steps")
    total_steps = cursor.fetchone()[0]
    
    print(f"  Total threads: {total_threads}")
    print(f"  Complete threads: {complete_count} ({'[OK] GOOD' if complete_count > 0 else '[WARN] NONE'})")
    print(f"  Pending threads: {pending_count} (transient state - hidden from users)")
    print(f"  Total steps: {total_steps}")
    
    # Final verdict
    print("\n" + "=" * 60)
    if complete_count > 0 and total_steps > 0:
        print("[PASS] Thread persistence working correctly!")
        if pending_count > 0:
            print("[INFO] Pending threads exist but are hidden from sidebar (OK)")
    elif complete_count == 0:
        print("[WARN] No complete threads found. Create a chat first.")
    elif total_steps == 0:
        print("[WARN] No steps found. Data might not be persisting.")
    else:
        print("[WARN] PARTIAL - Some issues detected, check details above.")
    print("=" * 60)
    
    conn.close()

if __name__ == "__main__":
    test_thread_persistence()

