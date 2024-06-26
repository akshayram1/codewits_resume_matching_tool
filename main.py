from collections import Counter
import streamlit as st
import nltk
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from nltk.tokenize import word_tokenize
from collections import Counter
import os
import PyPDF2
import pandas as pd
import re  # Added import for regular expressions
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx


nltk.download('punkt')


def extract_text_from_pdf(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page_num in range(len(pdf_reader.pages)):
        text += pdf_reader.pages[page_num].extract_text()
    return text


def extract_skills(text):
    skills_keywords = ["python", "java", "machine learning",
                       "data analysis", "communication", "problem solving"]
    skills = [skill.lower()
              for skill in skills_keywords if skill.lower() in text.lower()]
    return skills


def preprocess_text(text):
    return word_tokenize(text.lower())

# Function to extract CGPA from text using regular expressions


def extract_cgpa(text):
    # Pattern for CGPA (e.g., 3.75, 4.0, etc.)
    cgpa_pattern = r'\b(\d\.\d{1,2})/\d{1,2}|\b(\d\.\d{1,2})\b'
    cgpa_matches = re.findall(cgpa_pattern, text)
    return [float(match[0]) if match[0] else 0 for match in cgpa_matches]


email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
phone_pattern = r'\b\d{10}\b|\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'


def train_doc2vec_model(documents):
    model = Doc2Vec(vector_size=20, min_count=2, epochs=50)
    model.build_vocab(documents)
    model.train(documents, total_examples=model.corpus_count,
                epochs=model.epochs)
    return model


def calculate_similarity(model, text1, text2):
    vector1 = model.infer_vector(preprocess_text(text1))
    vector2 = model.infer_vector(preprocess_text(text2))
    return model.dv.cosine_similarities(vector1, [vector2])[0]


def v_spacer(height, sb=False) -> None:
    for _ in range(height):
        if sb:
            st.sidebar.write('\n')
        else:
            st.write('\n')


# Streamlit Frontend
st.title("Resume Matching Tool📃📃")

# Sidebar - File Upload for Resumes
st.sidebar.write("## Upload Resumes PDF")
resumes_files = st.sidebar.file_uploader(
    "Upload Resumes PDF", type=["pdf"], accept_multiple_files=True)
print("Resumes Uploaded:", resumes_files)

if resumes_files:
    # Sidebar - File Upload for Job Descriptions
    st.sidebar.write("## Upload Job Description PDF")
    job_descriptions_file = st.sidebar.file_uploader(
        "Upload Job Description PDF", type=["pdf"])

    if job_descriptions_file:
        # Sidebar - Sorting Options
        sort_options = ['Similarity Score', 'CGPA', 'Total Score']
        selected_sort_option = st.sidebar.selectbox(
            "Sort results by", sort_options)

        # Backend Processing
        job_description_text = extract_text_from_pdf(job_descriptions_file)
        resumes_texts = [extract_text_from_pdf(
            resume_file) for resume_file in resumes_files]
        print("Resumes Texts:", resumes_texts)

        # Calculate skills for all resumes
        all_resumes_skills = [extract_skills(
            resume_text) for resume_text in resumes_texts]

        tagged_resumes = [TaggedDocument(words=preprocess_text(
            text), tags=[str(i)]) for i, text in enumerate(resumes_texts)]
        model_resumes = train_doc2vec_model(tagged_resumes)

        results_data = {'Resume': [], 'Similarity Score': [],
                        'CGPA': [], 'Total Score': [], 'Email': [], 'Contact': []}

        for i, resume_text in enumerate(resumes_texts):
            similarity_score = calculate_similarity(
                model_resumes, resume_text, job_description_text)
            cgpa_values = extract_cgpa(resume_text)
            cgpa = ', '.join(map(str, cgpa_values)) if cgpa_values else '0'
            results_data['Resume'].append(resumes_files[i].name)
            smScore = similarity_score * 100
            total_score = smScore + sum(cgpa_values)
            results_data['Similarity Score'].append(smScore)
            results_data['CGPA'].append(cgpa)
            results_data['Total Score'].append(total_score)

            emails = ', '.join(re.findall(email_pattern, resume_text))
            contacts = ', '.join(re.findall(phone_pattern, resume_text))
            results_data['Email'].append(emails)
            results_data['Contact'].append(contacts)

        # Create a DataFrame
        results_df = pd.DataFrame(results_data)

        # Sort the DataFrame based on user-selected option
        if selected_sort_option == 'Similarity Score':
            results_df = results_df.sort_values(
                by='Similarity Score', ascending=False)
        elif selected_sort_option == 'CGPA':
            results_df = results_df.sort_values(by='CGPA', ascending=False)
        else:
            results_df = results_df.sort_values(
                by='Total Score', ascending=False)

        # Display the sorted results table
        st.subheader(f"Results Table (Sorted by {selected_sort_option}):")
        st.write(results_df)

        # Find the index of the highest similarity score
        highest_score_index = results_df['Similarity Score'].idxmax()
        highest_score_resume_name = resumes_files[highest_score_index].name
        # Details of Highest Similarity Score
        st.subheader("\nDetails of Highest Similarity Score Resume:")
        st.write(f"Resume Name: {highest_score_resume_name}")
        st.write(
            f"Similarity Score: {results_df.loc[highest_score_index, 'Similarity Score']:.2f}")

        # Check if 'CGPA' column exists in the DataFrame
        if 'CGPA' in results_df.columns:
            cgpa_value = results_df.loc[highest_score_index, 'CGPA']
            st.write(f"CGPA: {cgpa_value}" if pd.notnull(
                cgpa_value) else "CGPA: Not Mentioned")
        else:
            st.write("CGPA: Not Mentioned")

        # Check if 'Total Score' column exists in the DataFrame
        if 'Total Score' in results_df.columns:
            total_score_value = results_df.loc[highest_score_index,
                                               'Total Score']
            st.write(f"Total Score: {total_score_value:.2f}" if pd.notnull(
                total_score_value) else "Total Score: Not Mentioned")
        else:
            st.write("Total Score: Not Mentioned")

        # Check if 'Email' column exists in the DataFrame
        if 'Email' in results_df.columns:
            email_value = results_df.loc[highest_score_index, 'Email']
            st.write(f"Email: {email_value}" if pd.notnull(
                email_value) else "Email: Not Mentioned")
        else:
            st.write("Email: Not Mentioned")

        # Check if 'Contact' column exists in the DataFrame
        if 'Contact' in results_df.columns:
            contact_value = results_df.loc[highest_score_index, 'Contact']
            st.write(f"Contact: {contact_value}" if pd.notnull(
                contact_value) else "Contact: Not Mentioned")
        else:
            st.write("Contact: Not Mentioned")

        # Create a DataFrame for skills distribution
        skills_distribution_data = {'Resume': [], 'Skill': [], 'Frequency': []}
        for i, resume_skills in enumerate(all_resumes_skills):
            for skill in set(resume_skills):
                skills_distribution_data['Resume'].append(
                    resumes_files[i].name)
                skills_distribution_data['Skill'].append(skill)
                skills_distribution_data['Frequency'].append(
                    resume_skills.count(skill))

        skills_distribution_df = pd.DataFrame(skills_distribution_data)

        # Pivot the DataFrame for heatmap
        skills_heatmap_df = skills_distribution_df.pivot(
            index='Resume', columns='Skill', values='Frequency').fillna(0)

        # Normalize the values for better visualization
        skills_heatmap_df_normalized = skills_heatmap_df.div(
            skills_heatmap_df.sum(axis=1), axis=0)

        # Plot the heatmap
        fig, ax = plt.subplots(figsize=(12, 8))

        sns.heatmap(skills_heatmap_df_normalized,
                    cmap='YlGnBu', annot=True, fmt=".2f", ax=ax)
        ax.set_title('Heatmap for Skills Distribution')
        ax.set_xlabel('Resume')
        ax.set_ylabel('Skill')

        # Display the Matplotlib figure using st.pyplot()
        st.pyplot(fig)
    else:
        st.write("Please upload the Job Description PDF to proceed.")
else:
    st.write("Please upload Resumes PDF to proceed.")
