import streamlit as st
import requests
from streamlit_extras.colored_header import colored_header
import base64
from Frontend import add_custom_css
from pymongo.errors import DuplicateKeyError
import streamlit as st
import requests
import json
from datetime import datetime, date
from difflib import SequenceMatcher
from streamlit_extras.add_vertical_space import add_vertical_space
import requests
import os
from PIL import Image, ImageDraw, ImageFont
import io
import hashlib
import random
from Helper_Functions import *
import calendar

# --- EMBEDDED API KEYS ---
HYPERCLOVA_API_KEY = "nv-270db94eb8bf42108110b22f551e655axCwf"
LIBRARY_API_KEY = "70b5336f9e785c681d5ff58906e6416124f80f59faa834164d297dcd8db63036"

add_custom_css()

def main():
    import datetime
    import calendar
    
    # --- Initialize all session state variables before use ---
    if "api_key" not in st.session_state:
        st.session_state.api_key = HYPERCLOVA_API_KEY
    if "library_api_key" not in st.session_state:
        st.session_state.library_api_key = LIBRARY_API_KEY
    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "system",
            "content": (
                "You are a friendly AI assistant specializing in book recommendations. "
                "Start by greeting and asking about favorite books/authors/genres/age. "
                "For EVERY response, answer in BOTH English and Korean. "
                "First provide complete English answer, then '한국어 답변:' with Korean translation."
            )
        }]
    if "app_stage" not in st.session_state:
        st.session_state.app_stage = "welcome"
    if "books_data" not in st.session_state:
        st.session_state.books_data = []
    if "user_genre" not in st.session_state:
        st.session_state.user_genre = ""
    if "user_age" not in st.session_state:
        st.session_state.user_age = ""
    if "selected_book" not in st.session_state:
        st.session_state.selected_book = None
    if "showing_books" not in st.session_state:
        st.session_state.showing_books = False
    if "book_discussion_messages" not in st.session_state:
        st.session_state.book_discussion_messages = []
    if "book_intro_shown" not in st.session_state:
        st.session_state.book_intro_shown = False
    if "book_categories" not in st.session_state:
        st.session_state.book_categories = {}  # book_id: {category, status, start_date, end_date, hours_per_day}
    if "reading_schedule" not in st.session_state:
        st.session_state.reading_schedule = {}  # date: [book_info]
    if "selected_category_filter" not in st.session_state:
        st.session_state.selected_category_filter = "All"

    setup_sidebar()

    st.markdown("<h1 style='text-align:center;'>📚 Book Wanderer / 책방랑자</h1>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center;'>Discover your next favorite read with AI assistance in English and Korean</div>", unsafe_allow_html=True)
    st.markdown("---")

    # --- Chat history (only show non-book-specific messages in main flow) ---
    for msg in st.session_state.messages:
        if msg["role"] != "system" and not msg.get("book_context"):
            display_message(msg)

    # --- App stages ---
    if st.session_state.app_stage == "welcome":
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Hello! Tell me about your favourite books, author, genre, or age group. You can describe what you're looking for in natural language.\n\n한국어 답변: 안녕하세요! 좋아하는 책, 작가, 장르 또는 연령대에 대해 말씀해 주세요. 자연스러운 언어로 원하는 것을 설명해 주시면 됩니다."
        })
        st.session_state.app_stage = "awaiting_user_input"
        st.rerun()

    elif st.session_state.app_stage == "awaiting_user_input":
        col1, col2 = st.columns([4, 1])
        with col1:
            user_input = st.text_input("", key="user_open_input")
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("보내다 ᯓ➤", key="send_open_input"):
                if user_input:
                    st.session_state.messages.append({"role": "user", "content": user_input})
                    st.session_state.app_stage = "process_user_input"
                    st.rerun()

    elif st.session_state.app_stage == "process_user_input":
        user_input = st.session_state.messages[-1]["content"]
    
        # Detect if it's author or genre request
        dtl_code, dtl_label = get_dtl_kdc_code(user_input, HYPERCLOVA_API_KEY)
        
        if dtl_code and LIBRARY_API_KEY:
            if dtl_code == "AUTHOR":
                # Author-based search
                author_name = dtl_label
                books = get_books_by_author(author_name, LIBRARY_API_KEY, page_no=1, page_size=20)
                
                if books:
                    st.session_state.books_data = books
                    
                    # Generate AI response about the author's books
                    if HYPERCLOVA_API_KEY:
                        ai_response = call_hyperclova_api([
                            {"role": "system", "content": "You are a helpful book recommendation assistant. For EVERY response, answer in BOTH English and Korean. First provide complete English answer, then '한국어 답변:' with Korean translation."},
                            {"role": "user", "content": f"I found {len(books)} books by {author_name}. Tell me about this author and encourage me to explore their works."}
                        ], HYPERCLOVA_API_KEY)
                        
                        if ai_response:
                            st.session_state.messages.append({"role": "assistant", "content": ai_response})
                        else:
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": f"Excellent! I found {len(books)} books by {author_name}. This author has created diverse works that showcase their unique writing style and perspective. Take a look at their collection below!\n\n한국어 답변: 훌륭합니다! {author_name}의 책 {len(books)}권을 찾았습니다. 이 작가는 독특한 글쓰기 스타일과 관점을 보여주는 다양한 작품을 창작했습니다. 아래에서 그들의 컬렉션을 살펴보세요!"
                            })
                    
                    st.session_state.app_stage = "show_recommendations"
                else:
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": f"I couldn't find books by '{author_name}' in the library database. Could you try with a different spelling or another author? You can also try genre-based searches like 'mystery novels' or 'romance books'.\n\n한국어 답변: 도서관 데이터베이스에서 '{author_name}'의 책을 찾을 수 없었습니다. 다른 철자나 다른 작가로 시도해 보시겠어요? '추리소설'이나 '로맨스 소설' 같은 장르 기반 검색도 시도해 볼 수 있습니다."
                    })
                    st.session_state.app_stage = "awaiting_user_input"
            else:
                # Genre-based search (existing functionality)
                books = get_books_by_dtl_kdc(dtl_code, LIBRARY_API_KEY, page_no=1, page_size=20)
                
                if books:
                    st.session_state.books_data = books
                    
                    # Generate AI response about the recommendations using HyperCLOVA
                    if HYPERCLOVA_API_KEY:
                        ai_response = call_hyperclova_api([
                            {"role": "system", "content": "You are a helpful book recommendation assistant. For EVERY response, answer in BOTH English and Korean. First provide complete English answer, then '한국어 답변:' with Korean translation."},
                            {"role": "user", "content": f"I found {len(books)} books in the {dtl_label} category. Tell me about this category and encourage me to explore these recommendations."}
                        ], HYPERCLOVA_API_KEY)
                        
                        if ai_response:
                            st.session_state.messages.append({"role": "assistant", "content": ai_response})
                        else:
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": f"Great! I found {len(books)} excellent books in the {dtl_label} category. These recommendations are based on popularity and should match your interests perfectly. Take a look at the books below!\n\n한국어 답변: 좋습니다! {dtl_label} 카테고리에서 {len(books)}권의 훌륭한 책을 찾았습니다. 이 추천은 인기도를 바탕으로 하며 당신의 관심사와 완벽하게 일치할 것입니다. 아래 책들을 살펴보세요!"
                            })
                    
                    st.session_state.app_stage = "show_recommendations"
                else:
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": "I couldn't find books in that specific category. Could you try describing your preferences differently? For example, mention specific genres like 'mystery novels', 'self-help books', or 'Korean literature', or try searching by author name.\n\n한국어 답변: 해당 카테고리에서 책을 찾을 수 없었습니다. 다른 방식으로 선호도를 설명해 주시겠어요? 예를 들어 '추리소설', '자기계발서', '한국문학'과 같은 구체적인 장르를 언급하거나 작가 이름으로 검색해 보세요."
                    })
                    st.session_state.app_stage = "awaiting_user_input"
        else:
            missing_items = []
            if not dtl_code:
                missing_items.append("category/author matching")
            if not LIBRARY_API_KEY:
                missing_items.append("Library API key")
            
            error_msg = f"Unable to process your request due to: {', '.join(missing_items)}. Please check your API configuration in the sidebar."
            korean_msg = f"다음 이유로 요청을 처리할 수 없습니다: {', '.join(missing_items)}. 사이드바에서 API 설정을 확인해 주세요."
            
            st.session_state.messages.append({
                "role": "assistant", 
                "content": f"{error_msg}\n\n한국어 답변: {korean_msg}"
            })
            st.session_state.app_stage = "awaiting_user_input"
        
        st.rerun()

    elif st.session_state.app_stage == "show_recommendations":
        add_vertical_space(2)
        st.markdown("<h3 style='text-align:center;'>📖 Recommended Books for You</h3>", unsafe_allow_html=True)
        
        # Display books
        for i, book in enumerate(st.session_state.books_data[:10]):  # Show top 10 books
            display_book_card(book, i)
        
        # Chat input for follow-up questions
        col1, col2 = st.columns([4, 1])
        with col1:
            user_followup = st.text_input("Ask me anything about these books or request different recommendations:", key="followup_input")
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("보내다 ᯓ➤", key="send_followup"):
                if user_followup:
                    st.session_state.messages.append({"role": "user", "content": user_followup})
                    
                    # Check if user wants new recommendations
                    if any(keyword in user_followup.lower() for keyword in ['different', 'other', 'new', 'more', '다른', '새로운', '더']):
                        st.session_state.app_stage = "process_user_input"
                    else:
                        # Process as follow-up question using HyperCLOVA
                        response = process_followup_with_hyperclova(user_followup, HYPERCLOVA_API_KEY)
                        if response:
                            st.session_state.messages.append({"role": "assistant", "content": response})
                        else:
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": "I'd be happy to help you with more information about these books or other recommendations. What specific aspect would you like to know more about?\n\n한국어 답변: 이 책들에 대한 더 많은 정보나 다른 추천에 대해 기꺼이 도와드리겠습니다. 어떤 구체적인 측면에 대해 더 알고 싶으신가요?"
                            })
                    st.rerun()

    elif st.session_state.app_stage == "discuss_book":
        if st.session_state.selected_book:
            book = st.session_state.selected_book
            
            # Display selected book details
            add_vertical_space(2)
            st.markdown("<h3 style='text-align:center;'>📖 Let's Talk About This Book</h3>", unsafe_allow_html=True)
            
            with st.container():
                cols = st.columns([1, 2])
                with cols[0]:
                    image_url = book.get("bookImageURL", "")
                    if image_url:
                        st.image(image_url, width=200)
                    else:
                        st.markdown("""
                        <div style="width: 150px; height: 200px; background: linear-gradient(135deg, #2c3040, #363c4e); 
                                    display: flex; align-items: center; justify-content: center; border-radius: 8px;">
                            <span style="color: #b3b3cc;">No Image</span>
                        </div>
                        """, unsafe_allow_html=True)
                
                with cols[1]:
                    title = book.get('bookname') or book.get('bookName', 'Unknown Title')
                    authors = book.get('authors') or book.get('author', 'Unknown Author')
                    publisher = book.get('publisher', 'Unknown Publisher')
                    year = book.get('publication_year') or book.get('publicationYear', 'Unknown Year')
                    loan_count = book.get('loan_count') or book.get('loanCount', 0)
                    
                    st.markdown(f"""
                    <div style="padding: 20px;">
                        <h2 style="color: #2c3040; margin-bottom: 15px;">{title}</h2>
                        <div style="margin-bottom: 8px;"><strong>Author:</strong> {authors}</div>
                        <div style="margin-bottom: 8px;"><strong>Publisher:</strong> {publisher}</div>
                        <div style="margin-bottom: 8px;"><strong>Publication Year:</strong> {year}</div>
                        <div style="margin-bottom: 8px;"><strong>Popularity:</strong> {loan_count} loans</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Show introduction message when first entering book discussion
            if not st.session_state.book_intro_shown:
                intro_message = generate_book_introduction(book, HYPERCLOVA_API_KEY)
                st.session_state.book_discussion_messages.append({
                    "role": "assistant", 
                    "content": intro_message
                })
                st.session_state.book_intro_shown = True
                st.rerun()
            
            # Display chat history for this specific book
            for msg in st.session_state.book_discussion_messages:
                display_message(msg)
            
            # Chat input for book discussion with improved key management
            col1, col2 = st.columns([4, 1])
            with col1:
                book_question = st.text_input(
                    "Ask me anything about this book (plot, themes, similar books, etc.):", 
                    key=f"book_discussion_input_{len(st.session_state.book_discussion_messages)}"
                )
            
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("보내다 ᯓ➤", key=f"ask_about_book_{len(st.session_state.book_discussion_messages)}"):
                    if book_question:
                        # Add user message to book discussion
                        user_msg = {"role": "user", "content": book_question}
                        st.session_state.book_discussion_messages.append(user_msg)
                        
                        # Generate AI response about the book using HyperCLOVA
                        ai_response = process_book_question(
                            book, 
                            book_question, 
                            HYPERCLOVA_API_KEY,
                            st.session_state.book_discussion_messages
                        )
                        
                        assistant_msg = {"role": "assistant", "content": ai_response}
                        st.session_state.book_discussion_messages.append(assistant_msg)
                        
                        st.rerun()
            
            # Back to recommendations button
            if st.button("← Back to Recommendations", key="back_to_recs"):
                # Clear book discussion messages and intro flag when going back
                st.session_state.book_discussion_messages = []
                st.session_state.book_intro_shown = False
                st.session_state.app_stage = "show_recommendations"
                st.rerun()

    elif st.session_state.app_stage == "show_liked_books":
        add_vertical_space(2)
        st.markdown("<h3 style='text-align:center;'>❤️ My Library</h3>", unsafe_allow_html=True)
        
        if hasattr(st.session_state, 'username') and st.session_state.username:
            liked_books = get_liked_books(st.session_state.username)
            
            # Category filter
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            with col1:
                if st.button("All", key="filter_all"):
                    st.session_state.selected_category_filter = "All"
                    st.rerun()
            with col2:
                if st.button("To Read", key="filter_to_read"):
                    st.session_state.selected_category_filter = "To Read"
                    st.rerun()
            with col3:
                if st.button("Ongoing", key="filter_ongoing"):
                    st.session_state.selected_category_filter = "Ongoing"
                    st.rerun()
            with col4:
                if st.button("Finished", key="filter_finished"):
                    st.session_state.selected_category_filter = "Finished"
                    st.rerun()
            
            st.markdown("---")
            
            # Display reading calendar
            st.markdown("<h4 style='text-align:center;'>📅 Reading Calendar</h4>", unsafe_allow_html=True)
            
            # Calendar navigation
            today = datetime.date.today()
            cal_col1, cal_col2, cal_col3 = st.columns([1, 2, 1])
            
            with cal_col1:
                if st.button("← Previous Month", key="prev_month"):
                    if "current_month" not in st.session_state:
                        st.session_state.current_month = today.replace(day=1)
                    # Go to previous month
                    if st.session_state.current_month.month == 1:
                        st.session_state.current_month = st.session_state.current_month.replace(year=st.session_state.current_month.year-1, month=12)
                    else:
                        st.session_state.current_month = st.session_state.current_month.replace(month=st.session_state.current_month.month-1)
                    st.rerun()
            
            with cal_col2:
                if "current_month" not in st.session_state:
                    st.session_state.current_month = today.replace(day=1)
                st.markdown(f"<h5 style='text-align:center;'>{st.session_state.current_month.strftime('%B %Y')}</h5>", unsafe_allow_html=True)
            
            with cal_col3:
                if st.button("Next Month →", key="next_month"):
                    if "current_month" not in st.session_state:
                        st.session_state.current_month = today.replace(day=1)
                    # Go to next month
                    if st.session_state.current_month.month == 12:
                        st.session_state.current_month = st.session_state.current_month.replace(year=st.session_state.current_month.year+1, month=1)
                    else:
                        st.session_state.current_month = st.session_state.current_month.replace(month=st.session_state.current_month.month+1)
                    st.rerun()
            
            # Generate calendar
            cal = calendar.monthcalendar(st.session_state.current_month.year, st.session_state.current_month.month)
            
            # Calendar header
            days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            header_cols = st.columns(7)
            for i, day in enumerate(days):
                with header_cols[i]:
                    st.markdown(f"<div style='text-align:center; font-weight:bold; padding:5px;'>{day}</div>", unsafe_allow_html=True)
            
            # Calendar body
            for week in cal:
                week_cols = st.columns(7)
                for i, day in enumerate(week):
                    with week_cols[i]:
                        if day == 0:
                            st.markdown("<div style='height:60px;'></div>", unsafe_allow_html=True)
                        else:
                            current_date = datetime.date(st.session_state.current_month.year, st.session_state.current_month.month, day)
                            date_str = current_date.strftime('%Y-%m-%d')
                            
                            # Check if there are books scheduled for this date
                            books_for_date = []
                            for book_id, book_info in st.session_state.book_categories.items():
                                if book_info.get('start_date') and book_info.get('end_date'):
                                    start_date = datetime.datetime.strptime(book_info['start_date'], '%Y-%m-%d').date()
                                    end_date = datetime.datetime.strptime(book_info['end_date'], '%Y-%m-%d').date()
                                    if start_date <= current_date <= end_date and book_info.get('category') == 'Ongoing':
                                        # Find the book details
                                        for book in liked_books:
                                            book_title = book.get('bookname') or book.get('bookName', '')
                                            if str(book.get('id', '')) == str(book_id) or book_title == book_id:
                                                books_for_date.append(book_title[:15] + "..." if len(book_title) > 15 else book_title)
                                                break
                            
                            # Display date with books
                            if books_for_date:
                                books_text = "<br>".join(books_for_date[:2])  # Show max 2 books
                                if len(books_for_date) > 2:
                                    books_text += f"<br>+{len(books_for_date)-2} more"
                                
                                bg_color = "#e8f5e8" if current_date == today else "#f0f8ff"
                                st.markdown(f"""
                                <div style='background-color:{bg_color}; border:1px solid #ddd; padding:5px; 
                                           height:60px; overflow:hidden; font-size:10px; border-radius:3px;'>
                                    <strong>{day}</strong><br>
                                    <span style='color:#2c5aa0;'>{books_text}</span>
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                bg_color = "#fffacd" if current_date == today else "white"
                                st.markdown(f"""
                                <div style='background-color:{bg_color}; border:1px solid #ddd; padding:5px; 
                                           height:60px; text-align:center; border-radius:3px;'>
                                    <strong>{day}</strong>
                                </div>
                                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            if liked_books:
                # Filter books based on selected category
                filtered_books = []
                for book in liked_books:
                    book_id = str(book.get('id', '')) or book.get('bookname', '') or book.get('bookName', '')
                    book_category = st.session_state.book_categories.get(book_id, {}).get('category', 'To Read')
                    
                    if st.session_state.selected_category_filter == "All" or book_category == st.session_state.selected_category_filter:
                        filtered_books.append(book)
                
                st.markdown(f"**{st.session_state.selected_category_filter}**: {len(filtered_books)} books")
                
                for i, book in enumerate(filtered_books):
                    book_id = str(book.get('id', '')) or book.get('bookname', '') or book.get('bookName', '')
                    book_info = st.session_state.book_categories.get(book_id, {})
                    current_category = book_info.get('category', 'To Read')
                    
                    # Enhanced book card with scheduling
                    with st.container():
                        cols = st.columns([1, 3, 2])
                        
                        with cols[0]:
                            image_url = book.get("bookImageURL", "")
                            if image_url:
                                st.image(image_url, width=100)
                            else:
                                st.markdown("""
                                <div style="width: 80px; height: 120px; background: linear-gradient(135deg, #2c3040, #363c4e); 
                                            display: flex; align-items: center; justify-content: center; border-radius: 8px;">
                                    <span style="color: #b3b3cc; font-size: 10px;">No Image</span>
                                </div>
                                """, unsafe_allow_html=True)
                        
                        with cols[1]:
                            title = book.get('bookname') or book.get('bookName', 'Unknown Title')
                            authors = book.get('authors') or book.get('author', 'Unknown Author')
                            
                            st.markdown(f"**{title}**")
                            st.markdown(f"by {authors}")
                            
                            # Category status badge
                            status_colors = {
                                'To Read': '#ffa500',
                                'Ongoing': '#4caf50', 
                                'Finished': '#2196f3'
                            }
                            st.markdown(f"""
                            <span style='background-color: {status_colors[current_category]}; color: white; 
                                        padding: 2px 8px; border-radius: 12px; font-size: 12px;'>
                                {current_category}
                            </span>
                            """, unsafe_allow_html=True)
                            
                            # Show reading schedule info if available
                            if book_info.get('start_date') and book_info.get('end_date'):
                                st.markdown(f"📅 **Reading Period:** {book_info['start_date']} to {book_info['end_date']}")
                                if book_info.get('hours_per_day'):
                                    st.markdown(f"⏰ **Daily Reading:** {book_info['hours_per_day']} hours")
                        
                        with cols[2]:
                            # Category selection
                            new_category = st.selectbox(
                                "Status:", 
                                ["To Read", "Ongoing", "Finished"],
                                index=["To Read", "Ongoing", "Finished"].index(current_category),
                                key=f"category_{book_id}_{i}"
                            )
                            
                            # Update category if changed
                            if new_category != current_category:
                                if book_id not in st.session_state.book_categories:
                                    st.session_state.book_categories[book_id] = {}
                                st.session_state.book_categories[book_id]['category'] = new_category
                                
                                # Clear scheduling info if moving away from Ongoing
                                if new_category != 'Ongoing':
                                    st.session_state.book_categories[book_id].pop('start_date', None)
                                    st.session_state.book_categories[book_id].pop('end_date', None)
                                    st.session_state.book_categories[book_id].pop('hours_per_day', None)
                                
                                st.rerun()
                            
                            # Scheduling for "Ongoing" books
                            if new_category == "Ongoing":
                                st.markdown("**📅 Reading Schedule:**")
                                
                                # Hours per day input
                                hours_per_day = st.number_input(
                                    "Hours per day:",
                                    min_value=0.5,
                                    max_value=24.0,
                                    value=float(book_info.get('hours_per_day', 1.0)),
                                    step=0.5,
                                    key=f"hours_{book_id}_{i}"
                                )
                                
                                # Start date input
                                start_date = st.date_input(
                                    "Start date:",
                                    value=datetime.datetime.strptime(book_info.get('start_date', str(datetime.date.today())), '%Y-%m-%d').date() if book_info.get('start_date') else datetime.date.today(),
                                    key=f"start_{book_id}_{i}"
                                )
                                
                                # Calculate reading schedule button
                                if st.button("Calculate Schedule", key=f"calc_{book_id}_{i}"):
                                    # Estimate book length (pages) - using a heuristic based on typical book lengths
                                    # For demonstration, using average of 250-300 pages, can be enhanced with actual page data
                                    estimated_pages = 275  # Default estimate
                                    
                                    # Calculate reading speed (pages per hour) - average reader: 30-50 pages/hour
                                    pages_per_hour = 40  # Conservative estimate
                                    
                                    # Calculate total reading time needed
                                    total_hours_needed = estimated_pages / pages_per_hour
                                    
                                    # Calculate days needed based on hours per day
                                    days_needed = int(total_hours_needed / hours_per_day) + (1 if total_hours_needed % hours_per_day > 0 else 0)
                                    
                                    # Calculate end date
                                    end_date = start_date + datetime.timedelta(days=days_needed)
                                    
                                    # Update book info
                                    if book_id not in st.session_state.book_categories:
                                        st.session_state.book_categories[book_id] = {}
                                    
                                    st.session_state.book_categories[book_id].update({
                                        'category': 'Ongoing',
                                        'start_date': str(start_date),
                                        'end_date': str(end_date),
                                        'hours_per_day': hours_per_day,
                                        'estimated_pages': estimated_pages,
                                        'total_hours': total_hours_needed
                                    })
                                    
                                    # Update reading schedule
                                    current_date = start_date
                                    while current_date <= end_date:
                                        date_str = str(current_date)
                                        if date_str not in st.session_state.reading_schedule:
                                            st.session_state.reading_schedule[date_str] = []
                                        
                                        # Add book to this date if not already there
                                        book_entry = {
                                            'book_id': book_id,
                                            'title': title,
                                            'hours': hours_per_day
                                        }
                                        
                                        # Check if book is not already scheduled for this date
                                        if not any(entry['book_id'] == book_id for entry in st.session_state.reading_schedule[date_str]):
                                            st.session_state.reading_schedule[date_str].append(book_entry)
                                        
                                        current_date += datetime.timedelta(days=1)
                                    
                                    st.success(f"✅ Reading schedule calculated! You'll finish this book by {end_date.strftime('%B %d, %Y')}")
                                    st.rerun()
                                
                                # Show calculated schedule if available
                                if book_info.get('end_date'):
                                    end_date_obj = datetime.datetime.strptime(book_info['end_date'], '%Y-%m-%d').date()
                                    days_remaining = (end_date_obj - datetime.date.today()).days
                                    
                                    if days_remaining > 0:
                                        st.markdown(f"🎯 **Finish by:** {end_date_obj.strftime('%B %d, %Y')} ({days_remaining} days remaining)")
                                    elif days_remaining == 0:
                                        st.markdown(f"🎯 **Finish by:** Today!")
                                    else:
                                        st.markdown(f"📅 **Schedule:** Completed {abs(days_remaining)} days ago")
                                    
                                    if book_info.get('total_hours'):
                                        st.markdown(f"📖 **Estimated reading time:** {book_info['total_hours']:.1f} hours total")
                            
                            # Progress tracking for ongoing books
                            if current_category == "Ongoing" and book_info.get('start_date'):
                                start_date_obj = datetime.datetime.strptime(book_info['start_date'], '%Y-%m-%d').date()
                                days_since_start = (datetime.date.today() - start_date_obj).days
                                
                                if days_since_start >= 0:
                                    if book_info.get('end_date'):
                                        end_date_obj = datetime.datetime.strptime(book_info['end_date'], '%Y-%m-%d').date()
                                        total_days = (end_date_obj - start_date_obj).days
                                        progress_percentage = min(100, (days_since_start / total_days * 100)) if total_days > 0 else 0
                                        
                                        st.markdown(f"""
                                        <div style='background-color: #f0f0f0; border-radius: 10px; padding: 3px;'>
                                            <div style='background-color: #4caf50; width: {progress_percentage}%; height: 20px; 
                                                       border-radius: 10px; text-align: center; line-height: 20px; color: white; font-size: 12px;'>
                                                {progress_percentage:.1f}%
                                            </div>
                                        </div>
                                        """, unsafe_allow_html=True)
                        
                        st.markdown("---")
                
                # Reading Statistics
                st.markdown("---")
                st.markdown("<h4>📊 Reading Statistics</h4>", unsafe_allow_html=True)
                
                # Count books by category
                to_read_count = sum(1 for book_id, info in st.session_state.book_categories.items() if info.get('category', 'To Read') == 'To Read')
                ongoing_count = sum(1 for book_id, info in st.session_state.book_categories.items() if info.get('category') == 'Ongoing')
                finished_count = sum(1 for book_id, info in st.session_state.book_categories.items() if info.get('category') == 'Finished')
                
                # Ensure we count all books (those without explicit category are "To Read")
                total_categorized = to_read_count + ongoing_count + finished_count
                uncategorized = len(liked_books) - total_categorized
                to_read_count += uncategorized
                
                stat_col1, stat_col2, stat_col3 = st.columns(3)
                
                with stat_col1:
                    st.markdown(f"""
                    <div style='background-color: #fff3cd; padding: 15px; border-radius: 8px; text-align: center;'>
                        <h3 style='color: #856404; margin: 0;'>{to_read_count}</h3>
                        <p style='color: #856404; margin: 5px 0 0 0;'>To Read</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with stat_col2:
                    st.markdown(f"""
                    <div style='background-color: #d4edda; padding: 15px; border-radius: 8px; text-align: center;'>
                        <h3 style='color: #155724; margin: 0;'>{ongoing_count}</h3>
                        <p style='color: #155724; margin: 5px 0 0 0;'>Ongoing</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with stat_col3:
                    st.markdown(f"""
                    <div style='background-color: #cce7ff; padding: 15px; border-radius: 8px; text-align: center;'>
                        <h3 style='color: #004085; margin: 0;'>{finished_count}</h3>
                        <p style='color: #004085; margin: 5px 0 0 0;'>Finished</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Daily reading summary for today
                today_str = str(datetime.date.today())
                if today_str in st.session_state.reading_schedule:
                    st.markdown("---")
                    st.markdown("<h4>📖 Today's Reading Schedule</h4>", unsafe_allow_html=True)
                    
                    total_hours_today = 0
                    for book_entry in st.session_state.reading_schedule[today_str]:
                        st.markdown(f"• **{book_entry['title']}** - {book_entry['hours']} hours")
                        total_hours_today += book_entry['hours']
                    
                    st.markdown(f"**Total reading time today:** {total_hours_today} hours")
                
                # Weekly reading overview
                st.markdown("---")
                st.markdown("<h4>📅 This Week's Reading Plan</h4>", unsafe_allow_html=True)
                
                # Get start of current week (Monday)
                today = datetime.date.today()
                start_of_week = today - datetime.timedelta(days=today.weekday())
                
                weekly_schedule = {}
                total_weekly_hours = 0
                
                for i in range(7):  # 7 days in a week
                    current_day = start_of_week + datetime.timedelta(days=i)
                    day_str = str(current_day)
                    day_name = current_day.strftime('%A')
                    
                    if day_str in st.session_state.reading_schedule:
                        daily_hours = sum(entry['hours'] for entry in st.session_state.reading_schedule[day_str])
                        weekly_schedule[day_name] = {
                            'hours': daily_hours,
                            'books': len(st.session_state.reading_schedule[day_str])
                        }
                        total_weekly_hours += daily_hours
                    else:
                        weekly_schedule[day_name] = {'hours': 0, 'books': 0}
                
                # Display weekly overview
                week_cols = st.columns(7)
                for i, (day_name, day_info) in enumerate(weekly_schedule.items()):
                    with week_cols[i]:
                        bg_color = "#e8f5e8" if day_info['hours'] > 0 else "#f8f9fa"
                        st.markdown(f"""
                        <div style='background-color: {bg_color}; padding: 10px; border-radius: 5px; text-align: center; border: 1px solid #ddd;'>
                            <strong>{day_name[:3]}</strong><br>
                            <span style='color: #2c5aa0;'>{day_info['hours']}h</span><br>
                            <span style='font-size: 10px; color: #666;'>{day_info['books']} books</span>
                        </div>
                        """, unsafe_allow_html=True)
                
                if total_weekly_hours > 0:
                    st.markdown(f"**Total weekly reading time:** {total_weekly_hours} hours")
                else:
                    st.markdown("No reading scheduled for this week. Start planning your reading schedule!")
            
            else:
                st.markdown("Your library is empty. Start exploring books to add them to your collection!")
                if st.button("Discover Books", key="discover_from_empty"):
                    st.session_state.app_stage = "welcome"
                    st.rerun()
        else:
            st.error("Please ensure you are logged in to view your library.")
        
        # Back to main app button
        if st.button("← Back to Book Discovery", key="back_to_main"):
            st.session_state.app_stage = "show_recommendations" if st.session_state.books_data else "welcome"
            st.rerun()
