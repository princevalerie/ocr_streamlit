import os
import streamlit as st
import pandas as pd
import pytesseract
import cv2
import numpy as np
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv
import easyocr


# Load environment variables
load_dotenv()

class APIKeyManager:
    @staticmethod
    def get_gemini_api_key():
        """
        Mendapatkan API Key Gemini dengan aman
        """
        api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            st.sidebar.warning("Gemini API Key tidak ditemukan.")
            api_key = st.sidebar.text_input(
                "Masukkan Gemini API Key", 
                type="password",
                help="Dapatkan API key dari https://ai.google.dev"
            )
            
            if st.sidebar.button("Simpan Gemini API Key"):
                os.environ['GEMINI_API_KEY'] = api_key
                st.sidebar.success("API Key berhasil disimpan!")
        
        return api_key

class OCRService:
    @staticmethod
    def preprocess_image(image):
        """
        Pra-pemrosesan gambar untuk meningkatkan akurasi OCR
        """
        # Konversi ke grayscale
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        
        # Terapkan thresholding
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        
        return gray



class OCRService:
    @staticmethod
    def perform_ocr(image):
        try:
            # Inisialisasi reader (bisa tambahkan bahasa)
            reader = easyocr.Reader(['en', 'id'])
            
            # Konversi PIL Image ke numpy array
            img_array = np.array(image)
            
            # Lakukan OCR
            results = reader.readtext(img_array)
            
            # Gabungkan semua teks
            text = ' '.join([result[1] for result in results])
            
            return text
        except Exception as e:
            st.error(f"Kesalahan OCR: {e}")
            return None

class AIAnalysisService:
    @staticmethod
    def analyze_ocr_text(text, gemini_api_key):
        """
        Analisis teks OCR menggunakan Gemini AI
        """
        try:
            # Konfigurasi Gemini
            genai.configure(api_key=gemini_api_key)
            
            # Buat model
            model = genai.GenerativeModel('gemini-1.5-pro')
            
            # Prompt untuk ekstraksi data terstruktur
            prompt = f"""
            Ekstrak informasi dari teks berikut HANYA dalam format:
            'Tanggal Beli','Nama Item','Quantity','Harga','Total Harga'

            Contoh format keluaran:
            '2023-10-15','Oreo Vanilla','38','2000','76000'

            Aturan:
            - Gunakan tanda kutip tunggal
            - Pisahkan dengan koma
            - Jika data tidak ada, gunakan 'N/A'
            - Hanya kembalikan data, tanpa penjelasan tambahan

            Teks untuk diekstrak:
            {text}
            """
            
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            st.error(f"Kesalahan Analisis AI: {e}")
            return None

class AssetTrackingApp:
    def __init__(self):
        # Inisialisasi session state untuk tabel
        if 'asset_table' not in st.session_state:
            st.session_state.asset_table = pd.DataFrame(columns=[
                'Tanggal Beli', 'Nama Item', 'Quantity', 'Harga', 'Total Harga'
            ])
        
        if 'temp_table' not in st.session_state:
            st.session_state.temp_table = pd.DataFrame(columns=[
                'Tanggal Beli', 'Nama Item', 'Quantity', 'Harga', 'Total Harga'
            ])

    def run(self):
        st.title("🧾 Pencatatan Aset Tetap")
        
        # Konfigurasi API Key
        gemini_api_key = APIKeyManager.get_gemini_api_key()
        
        # Pilih mode
        mode = st.selectbox("Pilih Mode", ["Upload Gambar", "Gunakan Kamera"])
        
        if mode == "Upload Gambar":
            self.upload_mode(gemini_api_key)
        else:
            self.camera_mode(gemini_api_key)
        
        # Tabel Temporary
        st.subheader("Tabel Data Sementara")
        edited_table = st.data_editor(
            st.session_state.temp_table, 
            num_rows="dynamic", 
            key="temp_table_editor"
        )
        
        # Tombol untuk menyimpan data
        if st.button("Simpan Data ke Tabel Permanen"):
            # Gabungkan tabel permanen dengan data yang diedit
            st.session_state.asset_table = pd.concat([
                st.session_state.asset_table, 
                edited_table
            ], ignore_index=True)
            
            # Kosongkan tabel sementara
            st.session_state.temp_table = pd.DataFrame(columns=[
                'Tanggal Beli', 'Nama Item', 'Quantity', 'Harga', 'Total Harga'
            ])
            
            st.success("Data berhasil disimpan ke tabel permanen!")
        
        # Tampilkan tabel permanen
        st.subheader("Tabel Aset Permanen")
        st.dataframe(st.session_state.asset_table)

    def upload_mode(self, gemini_api_key):
        """
        Mode upload gambar
        """
        uploaded_file = st.file_uploader(
            "Upload Gambar Struk/Dokumen", 
            type=['png', 'jpg', 'jpeg']
        )
        
        if uploaded_file is not None:
            # Tampilkan gambar yang diunggah
            image = Image.open(uploaded_file)
            st.image(image, caption="Gambar Terunggah")
            
            if st.button("Proses Dokumen"):
                with st.spinner("Memproses Dokumen..."):
                    # Lakukan OCR
                    ocr_result = OCRService.perform_ocr(image)
                    
                    if ocr_result:
                        # Tampilkan hasil OCR
                        st.text_area("Hasil OCR", ocr_result, height=200)
                        
                        # Analisis dengan Gemini
                        analysis_result = AIAnalysisService.analyze_ocr_text(
                            ocr_result, 
                            gemini_api_key
                        )
                        
                        if analysis_result:
                            # Proses dan tampilkan hasil
                            self.process_analysis_result(analysis_result)

    def camera_mode(self, gemini_api_key):
        picture = st.camera_input("Ambil Gambar Struk")
        if picture is not None:
            # Tampilkan gambar yang diambil
            image = Image.open(picture)
            st.image(image, caption="Gambar dari Kamera")
            
            if st.button("Proses Dokumen"):
                with st.spinner("Memproses Dokumen..."):
                    # Lakukan OCR
                    ocr_result = OCRService.perform_ocr(image)
                    
                    if ocr_result:
                        # Tampilkan hasil OCR
                        st.text_area("Hasil OCR", ocr_result, height=200)
                        
                        # Analisis dengan Gemini
                        analysis_result = AIAnalysisService.analyze_ocr_text(
                            ocr_result, 
                            gemini_api_key
                        )
                        
                        if analysis_result:
                            # Proses dan tampilkan hasil
                            self.process_analysis_result(analysis_result)
                            
    def process_analysis_result(self, analysis_result):
        """
        Memproses hasil analisis dan menambahkannya ke tabel sementara
        """
        try:
            # Membersihkan dan memproses hasil analisis
            # Pisahkan baris-baris hasil
            lines = analysis_result.strip().split('\n')
            
            # Inisialisasi list untuk menyimpan data
            processed_data = []
            
            # Iterasi setiap baris
            for line in lines:
                # Hapus tanda kutip jika ada
                line = line.strip("'")
                
                # Split dengan koma atau tab
                parts = [part.strip("'") for part in line.split(',')]
                
                # Pastikan memiliki 5 kolom
                if len(parts) == 5:
                    processed_data.append(parts)
                elif len(parts) > 5:
                    # Jika lebih dari 5, gabungkan bagian nama item
                    modified_parts = [
                        parts[0],  # Tanggal
                        ' '.join(parts[1:-3]),  # Nama Item
                        parts[-3],  # Quantity
                        parts[-2],  # Harga
                        parts[-1]   # Total Harga
                    ]
                    processed_data.append(modified_parts)
            
            # Buat DataFrame
            if processed_data:
                df = pd.DataFrame(processed_data, columns=[
                    'Tanggal Beli', 'Nama Item', 'Quantity', 'Harga', 'Total Harga'
                ])
                
                # Bersihkan data yang mungkin kosong atau 'N/A'
                df = df[df['Nama Item'] != 'N/A']
                
                # Tambahkan ke tabel sementara
                st.session_state.temp_table = pd.concat([
                    st.session_state.temp_table, 
                    df
                ], ignore_index=True)
                
                # Tampilkan pesan sukses
                st.success(f"Berhasil menambahkan {len(df)} item ke tabel sementara!")
                
                # Tampilkan data yang ditambahkan
                st.dataframe(df)
            else:
                st.warning("Tidak ada data yang dapat diproses dari hasil analisis.")
        
        except Exception as e:
            st.error(f"Kesalahan saat memproses hasil analisis: {e}")
            # Tampilkan hasil asli untuk debugging
            st.text("Hasil Analisis Asli:")
            st.text(analysis_result)

def main():
    # Konfigurasi halaman Streamlit
    st.set_page_config(
        page_title="Pencatatan Aset Tetap",
        page_icon="🧾",
        layout="wide"
    )

    # Inisialisasi dan jalankan aplikasi
    app = AssetTrackingApp()
    app.run()

if __name__ == "__main__":
    main()
