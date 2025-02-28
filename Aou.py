import os
import json
import random
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# إعدادات عامة
BASE_DIR = "AOU"  # المجلد الرئيسي للمواد الدراسية
ADMIN_ID = 1635602338
BOT_TOKEN = "7701348977:AAH6xodvkhHhoVTzTpFmIihbe3vNL44m7FM"

# هياكل البيانات
students = {}  # بيانات الطلاب النشطين
current_question_index = {}  # تتبع تقدم الأسئلة
completed_exams = {}  # سجل الاختبارات المكتملة لكل طالب
student_names = {}  # 

# حالات المحادثة
ENTER_SECURITY_CODE, NUM_QUESTIONS, SELECT_PATH, START_EXAM = range(4)

def load_questions(file_path):
    """تحميل الأسئلة من ملف JSON"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أمر /start"""
    user = update.message.from_user
    greeting = f"مرحبًا {user.first_name}! لإجراء الاختبارات، أرسل /exam"
    if user.id == ADMIN_ID:
        greeting += "\nأنت المسؤول. استخدم /allow_exam للتحكم بالاختبارات"
    await update.message.reply_text(greeting)

async def allow_exam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """السماح بإجراء الاختبارات (للمسؤول فقط)"""
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ هذا الأمر متاح للمسؤول فقط")
        return
    
    await update.message.reply_text("🔐 أدخل رمز الأمان للطلاب:")
    return ENTER_SECURITY_CODE

async def handle_security_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رمز الأمان من المدير"""
    code = update.message.text.strip()
    if not code:
        await update.message.reply_text("⚠️ الرمز لا يمكن أن يكون فارغًا")
        return ENTER_SECURITY_CODE
    
    context.bot_data['security_code'] = code
    await update.message.reply_text("🔢 كم عدد الأسئلة في كل اختبار؟")
    return NUM_QUESTIONS

async def handle_num_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة عدد الأسئلة من المدير"""
    try:
        num = int(update.message.text)
        if num < 1:
            raise ValueError
            
        context.bot_data['num_questions'] = num
        msg = f"✅ تم التفعيل بنجاح!\nرمز الوصول: {context.bot_data['security_code']}"
        msg += f"\nعدد الأسئلة: {num}"
        await update.message.reply_text(msg)
        return ConversationHandler.END
    except:
        await update.message.reply_text("⚠️ أدخل رقمًا صحيحًا أكبر من الصفر")
        return NUM_QUESTIONS

async def start_exam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية الاختبار للطالب"""
    if 'security_code' not in context.bot_data:
        await update.message.reply_text("⏳ لم يتم تفعيل النظام بعد، تواصل مع المدير")
        return
    
    await update.message.reply_text("🔐 أدخل رمز الوصول:")
    return ENTER_SECURITY_CODE

async def handle_student_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التحقق من رمز الطالب"""
    user = update.message.from_user
    if update.message.text != context.bot_data.get('security_code'):
        await update.message.reply_text("❌ رمز خاطئ، حاول مجددًا")
        return ENTER_SECURITY_CODE
    
    # إعادة تعيين الحالة السابقة
    context.user_data.clear()
    current_question_index.pop(user.id, None)
    students.pop(user.id, None)
    
    context.user_data['current_path'] = BASE_DIR
    await show_folder_contents(update, context)
    return SELECT_PATH

# تعديلات على الكود الأصلي

async def show_folder_contents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض محتويات المجلد الحالي مع زر الرجوع"""
    current_path = context.user_data['current_path']
    items = os.listdir(current_path)
    
    folders = [i for i in items if os.path.isdir(os.path.join(current_path, i))]
    files = [i for i in items if i.endswith(".json")]
    
    keyboard = [[f] for f in folders]
    if files:
        keyboard.append(["بدء الاختبار 📝"])
    
    # إضافة زر الرجوع
    if current_path != BASE_DIR:
        keyboard.append(["الرجوع ↩️"])
    
    # إضافة زر العودة إلى الصفحة الرئيسية
    keyboard.append(["الصفحة الرئيسية 🏠"])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text(
        "اختر المادة الدراسية:",
        reply_markup=reply_markup
    )

async def handle_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة اختيار المستخدم مع دعم الرجوع والصفحة الرئيسية"""
    user = update.message.from_user
    choice = update.message.text
    current_path = context.user_data.get('current_path', BASE_DIR)
    
    # الرجوع إلى المجلد السابق
    if choice == "الرجوع ↩️":
        parent_path = os.path.dirname(current_path)
        if parent_path.startswith(BASE_DIR):
            context.user_data['current_path'] = parent_path
            await show_folder_contents(update, context)
            return SELECT_PATH
    
    # العودة إلى الصفحة الرئيسية
    if choice == "الصفحة الرئيسية 🏠":
        context.user_data.clear()
        current_question_index.pop(user.id, None)
        students.pop(user.id, None)
        context.user_data['current_path'] = BASE_DIR
        await show_folder_contents(update, context)
        return SELECT_PATH
    
    # باقي الخيارات كما هي
    if choice == "بدء الاختبار 📝":
        exam_file = os.path.join(current_path, "Questions.json")
        
        # التحقق من إتمام الاختبار لهذه المادة
        if completed_exams.get(user.id, {}).get(exam_file):
            keyboard = [["بدء اختبار جديد 🔄"], ["الصفحة الرئيسية 🏠"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            await update.message.reply_text(
                "❌ لقد أتممت هذا الاختبار مسبقًا",
                reply_markup=reply_markup
            )
            return SELECT_PATH
        
        # تحميل الأسئلة
        try:
            questions = load_questions(exam_file)
            num = context.bot_data.get('num_questions', len(questions))
            selected = random.sample(questions, min(num, len(questions)))
        except Exception as e:
            keyboard = [["بدء اختبار جديد 🔄"], ["الصفحة الرئيسية 🏠"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            await update.message.reply_text(
                "⚠️ حدث خطأ في تحميل الأسئلة",
                reply_markup=reply_markup
            )
            return SELECT_PATH
        
        # إعداد بيانات الطالب
        students[user.id] = {
            'score': 0,
            'answers': [],
            'exam_file': exam_file
        }
        current_question_index[user.id] = 0  # تهيئة المؤشر
        context.user_data['questions'] = selected
        
        # إشعار المدير
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"طالب جديد بدأ الاختبار: {user.first_name}\nالمادة: {os.path.basename(current_path)}"
        )
        
        await show_next_question(update, context)
        return START_EXAM
    
    elif choice == "بدء اختبار جديد 🔄":
        # إعادة تعيين الحالة وبدء الاختبار من جديد
        context.user_data.clear()
        current_question_index.pop(user.id, None)  # حذف المؤشر القديم إن وجد
        students.pop(user.id, None)  # حذف بيانات الطالب القديمة إن وجدت
        
        # إعادة تعيين المسار إلى المجلد الرئيسي
        context.user_data['current_path'] = BASE_DIR
        await show_folder_contents(update, context)
        return SELECT_PATH
    
    # التنقل بين المجلدات
    new_path = os.path.join(current_path, choice)
    if os.path.isdir(new_path): 
        context.user_data['current_path'] = new_path
        await show_folder_contents(update, context)
        return SELECT_PATH
    
    # إذا كان الخيار غير صالح
    keyboard = [["بدء اختبار جديد 🔄"], ["الصفحة الرئيسية 🏠"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text(
        "اختيار غير صالح، حاول مرة أخرى",
        reply_markup=reply_markup
    )
    return SELECT_PATH

async def show_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض السؤال التالي مع زر إعادة الاختبار"""
    user_id = update.message.from_user.id
    
    # التحقق من وجود بيانات الطالب
    if user_id not in current_question_index or user_id not in students:
        keyboard = [["بدء اختبار جديد 🔄"], ["الصفحة الرئيسية 🏠"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await update.message.reply_text(
            "⚠️ حدث خطأ أثناء عرض السؤال. يرجى المحاولة مرة أخرى.",
            reply_markup=reply_markup
        )
        return SELECT_PATH
    
    index = current_question_index[user_id]
    questions = context.user_data.get('questions')
    
    if not questions or index >= len(questions):
        await finish_exam(update, context)
        return
    
    question = questions[index]
    
    # تحديد نص السؤال بناءً على النوع
    q_text = f"السؤال {index+1}:"
    if question['type'] == 'text':
        q_text += f"\n{question['question']}"
    elif question['type'] == 'image':
        q_text += "\nسؤال بصورة"
        img_path = question['question_image']
        try:
            with open(img_path, 'rb') as photo:
                await update.message.reply_photo(photo, caption=q_text)
        except FileNotFoundError:
            keyboard = [["بدء اختبار جديد 🔄"], ["الصفحة الرئيسية 🏠"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            await update.message.reply_text(
                "⚠️ لم يتم العثور على صورة السؤال.",
                reply_markup=reply_markup
            )
            return
    
    # إذا كان السؤال نصيًا، يتم عرض النص فقط
    if question['type'] == 'text':
        await update.message.reply_text(q_text)
    
    # عرض الخيارات
    options = question['options']
    keyboard = [[o] for o in options]
    keyboard.append(["إعادة الاختبار الحالي 🔁"])  # زر إعادة الاختبار
    keyboard.append(["الصفحة الرئيسية 🏠"])  # زر العودة إلى الصفحة الرئيسية
    await update.message.reply_text(
        "اختر الإجابة:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة إجابة الطالب مع دعم إعادة الاختبار"""
    user_id = update.message.from_user.id
    answer = update.message.text
    
    # إذا اختار الطالب إعادة الاختبار الحالي
    if answer == "إعادة الاختبار الحالي 🔁":
        # إعادة تهيئة بيانات الطالب دون تغيير المسار
        current_path = context.user_data.get('current_path', BASE_DIR)
        exam_file = os.path.join(current_path, "Questions.json")
        
        try:
            questions = load_questions(exam_file)
            num = context.bot_data.get('num_questions', len(questions))
            selected = random.sample(questions, min(num, len(questions)))
        except Exception as e:
            keyboard = [["بدء اختبار جديد 🔄"], ["الصفحة الرئيسية 🏠"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            await update.message.reply_text(
                "⚠️ حدث خطأ في تحميل الأسئلة",
                reply_markup=reply_markup
            )
            return SELECT_PATH
        
        # إعادة تهيئة بيانات الطالب
        students[user_id] = {
            'score': 0,
            'answers': [],
            'exam_file': exam_file
        }
        current_question_index[user_id] = 0  # تهيئة المؤشر
        context.user_data['questions'] = selected
        
        # إشعار المدير
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"طالب أعاد الاختبار: {update.message.from_user.first_name}\nالمادة: {os.path.basename(current_path)}"
        )
        
        await show_next_question(update, context)
        return START_EXAM
    
    # إذا اختار الطالب العودة إلى الصفحة الرئيسية
    if answer == "الصفحة الرئيسية 🏠":
        context.user_data.clear()
        current_question_index.pop(user_id, None)
        students.pop(user_id, None)
        context.user_data['current_path'] = BASE_DIR
        await show_folder_contents(update, context)
        return SELECT_PATH
    
    # باقي المعالجة كما هي
    if user_id not in current_question_index or user_id not in students:
        await update.message.reply_text("⚠️ هل أنت متأكد؟ يرجى الإدخال مرة أخرى.")
        return SELECT_PATH
    
    index = current_question_index[user_id]
    questions = context.user_data.get('questions')
    student = students[user_id]
    
    if not questions or index >= len(questions):
        await finish_exam(update, context)
        return
    
    # التحقق من الإجابة
    question = questions[index]
    correct_answer = question['options'][question['correct']]
    is_correct = (answer == correct_answer)
    
    # تسجيل النتيجة
    student['answers'].append({
        'question': question.get('question', 'سؤال بصورة'),
        'user_answer': answer,
        'is_correct': is_correct,
        'correct_answer': correct_answer
    })
    
    if is_correct:
        student['score'] += 1 
    
    # الانتقال للسؤال التالي
    current_question_index[user_id] += 1
    await show_next_question(update, context)
async def finish_exam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إنهاء الاختبار وعرض النتائج"""
    user_id = update.message.from_user.id
    
    # التحقق من وجود بيانات الطالب
    if user_id not in students or user_id not in current_question_index:
        keyboard = [["بدء اختبار جديد 🔄"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await update.message.reply_text(
            "⚠️ حدث خطأ أثناء إنهاء الاختبار. يرجى المحاولة مرة أخرى.",
            reply_markup=reply_markup
        )
        return SELECT_PATH
    
    student = students[user_id]
    
    # إعداد التقرير للطالب
    report = f"✅ انتهى الاختبار!\nالنتيجة: {student['score']}/{len(student['answers'])}\n\n"
    wrong_answers = []
    for i, ans in enumerate(student['answers'], 1):
        status = "صحيح" if ans['is_correct'] else "خطأ"
        report += f"سؤال {i}: {ans['question']}\nإجابتك: {ans['user_answer']} ({status})\n\n"
        if not ans['is_correct']:
            wrong_answers.append(f"سؤال {i}: {ans['question']}\nإجابتك: {ans['user_answer']}\nالإجابة الصحيحة: {ans['correct_answer']}\n")
    
    # إظهار الأسئلة الخاطئة
    if wrong_answers:
        wrong_report = "❌ الأسئلة الخاطئة:\n" + "\n".join(wrong_answers)
        await update.message.reply_text(wrong_report)
    
    # إرسال النتائج إلى الطالب
    await update.message.reply_text(report)
    
    # تحديث السجلات
    exam_file = student['exam_file']
    if user_id not in completed_exams:
        completed_exams[user_id] = {}
    completed_exams[user_id][exam_file] = True
    
    # إعداد مسار المادة
    material_path = exam_file.replace(BASE_DIR, "").strip("/").replace("/", " - ")
    
    # إرسال تقرير إلى المدير
    admin_report = (
        f"📝 تقرير اختبار جديد:\n"
        f"اسم الطالب: {update.message.from_user.first_name}\n"
        f"المادة: {material_path}\n"
        f"النتيجة: {student['score']}/{len(student['answers'])}"
    )
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_report)
    
    # إرسال الإحصائيات إلى المدير
    stats = get_statistics()
    await context.bot.send_message(chat_id=ADMIN_ID, text=stats)
    
    # تنظيف البيانات
    del students[user_id]
    del current_question_index[user_id]
    context.user_data.clear()
    
    # تقديم خيار للطالب لبدء اختبار جديد
    keyboard = [["بدء اختبار جديد 🔄"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text(
        "ماذا تريد أن تفعل الآن؟",
        reply_markup=reply_markup
    )
    return SELECT_PATH
def get_statistics():
    """إعداد الإحصائيات العامة"""
    total_students = len(completed_exams)
    total_tests = sum(len(tests) for tests in completed_exams.values())
    stats = f"📊 إحصائيات عامة:\nعدد الطلاب الكلي: {total_students}\nعدد الاختبارات المنفذة: {total_tests}\n\n"
    
    for user_id, exams in completed_exams.items():
        student_name = student_names.get(user_id, "غير معروف")  # الحصول على اسم الطالب
        student_stats = f"طالب: {student_name} (ID: {user_id})\nعدد الاختبارات: {len(exams)}\n"
        for exam_file, completed in exams.items():
            material_path = exam_file.replace(BASE_DIR, "").strip("/").replace("/", " - ")
            student_stats += f"- المادة: {material_path}\n"
        stats += student_stats + "\n"
    
    return stats
def main():
    """إعداد وتشغيل البوت"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    # معالجات الأوامر
    app.add_handler(CommandHandler("start", start))
    
    # محادثة المدير
    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("allow_exam", allow_exam)],
        states={
            ENTER_SECURITY_CODE: [MessageHandler(filters.TEXT, handle_security_code)],
            NUM_QUESTIONS: [MessageHandler(filters.TEXT, handle_num_questions)]
        },
        fallbacks=[]
    )
    app.add_handler(admin_conv)
    
    # محادثة الطالب
    student_conv = ConversationHandler(
        entry_points=[CommandHandler("exam", start_exam)],
        states={
            ENTER_SECURITY_CODE: [MessageHandler(filters.TEXT, handle_student_code)],
            SELECT_PATH: [MessageHandler(filters.TEXT, handle_selection)],
            START_EXAM: [MessageHandler(filters.TEXT, handle_answer)]
        },
        fallbacks=[]
    )
    app.add_handler(student_conv)
    
    app.run_polling()

if __name__ == "__main__":
    main()