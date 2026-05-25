async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global registration_open

    q = update.callback_query
    await q.answer()

    user = q.from_user
    uid = user.id
    name = user.first_name

    # 🚫 منع المحظور
    if uid in blocked:
        await q.answer("🚫 أنتِ محظورة", show_alert=True)
        return

    data = q.data

    # 🔒 لو التسجيل مغلق → لا تعديل ولا إعادة رسالة
    if not registration_open and data in ["reg", "read", "listen", "excused"]:
        await q.answer("🔒 التسجيل مغلق", show_alert=True)
        return

    # ===== العمليات =====
    if data == "reg":
        registered[uid] = name

    elif data == "read":
        if uid in registered:
            readers.add(name)

    elif data == "listen":
        listeners.add(name)
        registered.pop(uid, None)
        readers.discard(name)
        excused.discard(name)

    elif data == "excused":
        excused.add(name)
        registered.pop(uid, None)
        readers.discard(name)
        listeners.discard(name)

    elif data == "toggle":
        registration_open = not registration_open

    elif data == "reset":
        registered.clear()
        readers.clear()
        listeners.clear()
        excused.clear()

    # ✔ تحديث فقط عند وجود تغيير فعلي
    await q.edit_message_text(build_text(), reply_markup=menu())
