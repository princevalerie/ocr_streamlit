import os
import streamlit as st
import pandas as pd
import base64
import io
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv
import datetime

# Muat variabel lingkungan
load_dotenv()

class OCRService:
    @staticmethod
    def image_to_base64(image):
        """
        Konversi gambar ke base64
        """
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

    @staticmethod
    def perform_ocr(image, gemini_api_key):
        """
        Melakukan OCR menggunakan Gemini 1.5 Flash
        """
        try:
            # Konfigurasi Gemini
            genai.configure(api_key=gemini_api_key)
            
            # Konversi gambar ke base64
            base64_image = OCRService.image_to_base64(image)
            
            # Buat model
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Prompt untuk ekstraksi teks dari gambar
            prompt = """
            Ekstrak informasi detail dari struk/dokumen dengan presisi tinggi:

            Panduan Ekstraksi:
            1. Identifikasi dengan jelas setiap komponen
            2. Fokus pada informasi penting
            3. Perhatikan format angka dan tanggal

            Informasi yang WAJIB diekstrak:
            - Tanggal Transaksi (format YYYY-MM-DD)
            - Nama Produk/Item (nama lengkap)
            - Harga Satuan (dalam angka)
            - Jumlah/Quantity (angka)
            - Total Harga (jika sudah ada maka tulis jika tidak maka hasil perkalian harga satuan dengan quantity)

            Catatan Penting:
            - Gunakan format numerik yang bersih
            - Hilangkan simbol mata uang
            - Jika informasi tidak ditemukan, gunakan 'N/A'
            - Prioritaskan keakuratan data
            """
            
            # Proses gambar
            response = model.generate_content([prompt, {'mime_type': 'image/png', 'data': base64_image}])
            
            return response.text
        except Exception as e:
            st.error(f"Kesalahan OCR: {e}")
            return None
        
@staticmethod
def perform_ocr(image, gemini_api_key):
    """
    Melakukan OCR menggunakan Gemini 1.5 Flash
    """
    try:
        # Konfigurasi Gemini
        genai.configure(api_key=gemini_api_key)
        
        # Konversi gambar ke base64
        base64_image = OCRService.image_to_base64(image) #ganti ini dengangemini flash saja karena tidak ada osr service
        
        # Buat model
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Prompt untuk ekstraksi teks dari gambar
        prompt = """
        Ekstrak informasi penting dari gambar struk/dokumen:
        - Nama Item/Produk
        - Harga Satuan
        - Quantity
        - Total Harga
        - Tanggal Transaksi

        Berikan output terstruktur.
        """
        
        # Proses gambar
        response = model.generate_content([prompt, {'mime_type': 'image/png', 'data': base64_image}])
        
        return response.text
    except Exception as e:
        st.error(f"Kesalahan OCR: {e}")
        return None

class AIAnalysisService:
    @staticmethod
    def analyze_ocr_text(text, gemini_api_key):
        try:
            # Konfigurasi Gemini
            genai.configure(api_key=gemini_api_key)
            
            # Buat model
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Prompt untuk ekstraksi data terstruktur
            prompt = f"""
            Instruksi Ekstraksi Data Terperinci:

            Sumber Teks:
            {text}

            Panduan Ekstraksi:
            1. Ekstrak data dengan format CSV yang ketat
            2. Setiap kolom memiliki kriteria spesifik

            Format Keluaran PASTI:
            'Tanggal Beli','Nama Item','Quantity','Harga','Total Harga'

            Aturan Ketat:
            - Gunakan tanda kutip tunggal
            - Pisahkan dengan koma TEPAT
            - Tanggal: format YYYY-MM-DD
            - Nama Item: nama lengkap, hilangkan karakter khusus
            - Quantity: bilangan bulat positif
            - Harga: bilangan bulat, tanpa simbol mata uang
            - Total Harga: hasil perkalian Quantity * Harga

            Contoh Valid:
            '2023-10-15','Oreo Vanilla','38','2000','76000'

            Instruksi Akhir:
            - Kembalikan HANYA data dalam format CSV
            - Jangan tambahkan penjelasan atau komentar
            - Prioritaskan presisi dan konsistensi
            """
            
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            st.error(f"Kesalahan Analisis: {e}")
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
        
        # Input API Key
        gemini_api_key = os.getenv('GEMINI_API_KEY')
    
        # Pilih mode input
        mode = st.selectbox("Pilih Mode Input", 
            ["Upload Gambar", "Input Manual", "Scan Kamera"]
        )
    
        # Proses berdasarkan mode
        if mode == "Upload Gambar" and gemini_api_key:
            self.upload_image_mode(gemini_api_key)
        elif mode == "Input Manual":
            self.manual_input_mode()
        elif mode == "Scan Kamera" and gemini_api_key:
            self.camera_scan_mode(gemini_api_key)
    
        # Tampilkan tabel sementara
        st.subheader("Tabel Data Sementara")
        
        # Kolom untuk tombol reset
        col1, col2 = st.columns([3, 1])
        
        with col2:
            # Tombol reset tabel sementara dengan konfirmasi
            if st.button("🗑️ Reset Tabel", type="primary"):
                # Tampilkan modal konfirmasi
                with st.expander("Konfirmasi Reset"):
                    st.warning("Apakah Anda yakin ingin mereset tabel sementara?")
                    
                    # Tombol konfirmasi
                    if st.button("Ya, Reset Tabel"):
                        # Reset HANYA tabel sementara
                        st.session_state.temp_table = pd.DataFrame(columns=[
                            'Tanggal Beli', 'Nama Item', 'Quantity', 'Harga', 'Total Harga'
                        ])
                        st.success("Tabel sementara berhasil direset!")
                    
                    # Tombol batal
                    if st.button("Batal"):
                        st.stop()
        
        # Edit tabel dengan opsi dinamis
        with col1:
            edited_table = st.data_editor(
                st.session_state.temp_table, 
                num_rows="dynamic"
            )
    
        # Tombol simpan ke tabel permanen
        if st.button("Simpan ke Tabel Permanen"):
            # Gabungkan tabel permanen dengan data yang diedit
            st.session_state.asset_table = pd.concat([
                st.session_state.asset_table, 
                edited_table
            ], ignore_index=True)
            
            # Reset tabel sementara
            st.session_state.temp_table = pd.DataFrame(columns=[
                'Tanggal Beli', 'Nama Item', 'Quantity', 'Harga', 'Total Harga'
            ])
            
            st.success("Data berhasil disimpan!")
    
        # Tampilkan tabel permanen
        st.subheader("Tabel Aset Permanen")
        st.dataframe(st.session_state.asset_table)
    
        # Tambahan: Tombol hapus tabel permanen (opsional)
        if st.checkbox("Tampilkan opsi hapus tabel permanen"):
            if st.button("🗑️ Hapus Seluruh Tabel Permanen", type="primary"):
                # Konfirmasi sebelum menghapus
                confirm = st.checkbox("Saya yakin ingin menghapus SELURUH tabel permanen")
                
                if confirm:
                    st.session_state.asset_table = pd.DataFrame(columns=[
                        'Tanggal Beli', 'Nama Item', 'Quantity', 'Harga', 'Total Harga'
                    ])
                    st.warning("Seluruh tabel permanen telah dihapus!")

    def upload_image_mode(self, gemini_api_key):
        uploaded_file = st.file_uploader(
            "Upload Gambar Struk/Dokumen", 
            type=['png', 'jpg', 'jpeg']
        )
        
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="Gambar Terunggah", width=300)
            
            if st.button("Proses Dokumen"):
                with st.spinner("Memproses Dokumen..."):
                    ocr_result = OCRService.perform_ocr(image, gemini_api_key)
                    
                    if ocr_result:
                        st.text_area("Hasil OCR", ocr_result, height=200)
                        
                        analysis_result = AIAnalysisService.analyze_ocr_text(
                            ocr_result, 
                            gemini_api_key
                        )
                        
                        if analysis_result:
                            self.process_analysis_result(analysis_result)

    def camera_scan_mode(self, gemini_api_key):
        picture = st.camera_input("Ambil Gambar Struk")
        
        if picture is not None:
            image = Image.open(picture)
            st.image(image, caption="Gambar dari Kamera", width=300)
            
            if st.button("Proses Dokumen"):
                with st.spinner("Memproses Dokumen..."):
                    ocr_result = OCRService.perform_ocr(image, gemini_api_key)
                    
                    if ocr_result:
                        st.text_area("Hasil OCR", ocr_result, height=200)
                        
                        analysis_result = AIAnalysisService.analyze_ocr_text(
                            ocr_result, 
                            gemini_api_key
                        )
                        
                        if analysis_result:
                            self.process_analysis_result(analysis_result)

    def manual_input_mode(self):
        st.subheader("Input Manual Data Aset")
        
        # Kolom input
        col1, col2 = st.columns(2)
        
        with col1:
            tanggal_beli = st.date_input("Tanggal Beli")
            nama_item = st.text_input("Nama Item")
            
        with col2:
            quantity = st.number_input("Quantity", min_value=1, value=1)
            harga = st.number_input("Harga Satuan", min_value=0, value=0)

        # Hitung total harga
        total_harga = quantity * harga

        # Tampilkan hasil
        st.write(f"**Total Harga:** {total_harga}")

        # Tombol tambah ke tabel sementara
        if st.button("Tambah ke Tabel Sementara"):
            # Tambahkan data ke tabel sementara
            new_data = pd.DataFrame([{
                'Tanggal Beli': tanggal_beli.strftime('%Y-%m-%d'),
                'Nama Item': nama_item,
                'Quantity': quantity,
                'Harga': harga,
                'Total Harga': total_harga
            }])

            st.session_state.temp_table = pd.concat(
                [st.session_state.temp_table, new_data],
                ignore_index=True
            )

            st.success("Data berhasil ditambahkan ke tabel sementara!")

    def process_analysis_result(self, analysis_result):
        try:
            # Bersihkan hasil dari karakter ekstra
            clean_result = analysis_result.strip().replace("'", "")
            
            # Split baris
            lines = clean_result.split('\n')
            
            # Inisialisasi list untuk data
            processed_data = []
            
            for line in lines:
                # Split dengan koma
                parts = [part.strip() for part in line.split(',')]
                
                # Validasi panjang data
                if len(parts) == 5:
                    processed_data.append(parts)
            
            # Buat DataFrame
            if processed_data:
                df = pd.DataFrame(processed_data, columns=[
                    'Tanggal Beli', 'Nama Item', 'Quantity', 'Harga', 'Total Harga'
                ])
                
                # Konversi tipe data
                df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
                df['Harga'] = pd.to_numeric(df['Harga'], errors='coerce')
                df['Total Harga'] = pd.to_numeric(df['Total Harga'], errors='coerce')
                
                # Bersihkan data yang tidak valid
                df = df.dropna()
                
                # Tambahkan ke tabel sementara
                st.session_state.temp_table = pd.concat([
                    st.session_state.temp_table, 
                    df
                ], ignore_index=True)
                
                st.success(f"Berhasil menambahkan {len(df)} item ke tabel sementara!")
                st.dataframe(df)
            else:
                st.warning("Tidak ada data yang dapat diproses.")
        
        except Exception as e:
            st.error(f"Kesalahan saat memproses hasil analisis: {e}")
            st.text("Hasil Analisis Asli:")
            st.text(analysis_result)


# Jalankan aplikasi
if __name__ == "__main__":
    app = AssetTrackingApp()
    app.run()
            
 
