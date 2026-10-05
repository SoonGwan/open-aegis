"""Task terminal state and its typed notification source share one durable audit commit."""
def terminal(store,task_id,changes,message,level='info',detail=None):
    status=changes['status']
    if status not in ('completed','failed','stopped','interrupted','rejected'):raise ValueError('terminal_status')
    with store.lock,store.write_transaction() as db:
        before=store.get('tasks',task_id,connection=db)
        if before is None:raise KeyError(task_id)
        after={**before,**changes}
        store.put_many([('tasks',after)],connection=db)
        store.event(task_id,message,level,{**(detail or {}),'notification_kind':'task.terminal','task_status':status},connection=db)
        return after
