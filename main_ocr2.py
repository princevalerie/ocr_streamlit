import os
import streamlit as st
import pandas as pd
import base64
import io
import re
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv
import datetime

# Muat variabel lingkungan
load_dotenv()

class SatuanConverter:
    @staticmethod
    def convert_fractions(value):
        """
        Konversi pecahan menjadi float
        """
        try:
            # Tangani pecahan campuran
            if isinstance(value, str):
                # Pecahan campuran seperti "1 1/2"
                if ' ' in value:
                    whole, frac = value.split(' ')
                    return float(whole) + SatuanConverter.fraction_to_float(frac)
                
                # Pecahan sederhana seperti "1/2"
                if '/' in value:
                    return SatuanConverter.fraction_to_float(value)
                
                # Konversi string ke float
                return float(value)
            
            return float(value)
        except Exception as e:
            st.warning(f"Kesalahan konversi: {e}")
            return 0.0

    @staticmethod
    def fraction_to_float(fraction):
        """
        Konversi pecahan menjadi float
        """
        try:
            num, denom = map(int, fraction.split('/'))
            return num / denom
        except Exception as e:
            st.warning(f"Kesalahan konversi pecahan: {e}")
            return 0.0

class DataValidator:
    @staticmethod
    def validate_input(data):
        """
        Validasi data input
        """
        errors = []
        
        # Validasi Nama Item
        if not data['Nama Item'] or len(data['Nama Item']) < 2:
            errors.append("Nama Item minimal 2 karakter")
        
        # Validasi Quantity
        if data['Quantity'] <= 0:
            errors.append("Quantity harus lebih dari 0")
        
        # Validasi Harga
        if data['Harga'] < 0:
            errors.append("Harga tidak boleh negatif")
        
        # Validasi Vendor
        if not data['Vendor'] or len(data['Vendor']) < 2:
            errors.append("Nama Vendor minimal 2 karakter")
        
        return errors

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
            4. Konversi pecahan menjadi desimal

            Informasi yang WAJIB diekstrak:
            - Tanggal Transaksi (format YYYY-MM-DD)
            - Nama Produk/Item (nama lengkap)
            - Harga Satuan (dalam angka)
            - Jumlah/Quantity (angka atau pecahan)
            - Jenis Satuan (contoh: pcs, kg, meter, lembar, pack)
            - Total Harga 
            - Vendor (Nama toko/tempat)

            Aturan Jenis Satuan:
            - Gunakan satuan umum yang ada di struk
            - Jika tidak ada, tuliskan N/A
            - Pastikan satuan sesuai dengan jenis produk

            Catatan Penting:
            - Gunakan format numerik yang bersih
            - Konversi pecahan (mis. 1/2 → 0.5)
            - Hilangkan simbol mata uang
            - Prioritaskan keakuratan data
            - Jika yang lain tidak ada, tuliskan N/A
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
            3. Konversi pecahan ke desimal

            Format Keluaran PASTI:
            'Tanggal Beli','Nama Item','Quantity','Jenis Satuan','Harga','Total Harga','Vendor'

            Aturan Ketat:
            - Gunakan tanda kutip tunggal
            - Pisahkan dengan koma TEPAT
            - Tanggal: format YYYY-MM-DD
            - Nama Item: nama lengkap, hilangkan karakter khusus 
            - Quantity: bilangan desimal (konversi pecahan)
            - Jenis Satuan: satuan yang sesuai dengan produk (pcs, kg, meter, dll)
            - Harga: bilangan bulat, tanpa simbol mata uang
            - Total Harga: hasil perkalian Quantity * Harga
            - Vendor: Nama toko pada struk

            Contoh Valid:
            '2023-10-15','Semen Tiga Roda','1.5','kg','50000','75000','Toko Bangunan'

            Instruksi Akhir:
            - Kembalikan HANYA data dalam format CSV
            - Jangan tambahkan penjelasan atau komentar
            - Prioritaskan presisi dan konsistensi
            - Apabila banyak N/A tetap masukkan ke tabel
            """
            
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            st.error(f"Kesalahan Analisis: {e}")
            return None

class ExportService:
    @staticmethod
    def export_to_csv(dataframe, filename='asset_data.csv'):
        """
        Ekspor DataFrame ke CSV
        """
        try:
            # Simpan ke file CSV
            dataframe.to_csv(filename, index=False)
            return filename
        except Exception as e:
            st.error(f"Gagal mengekspor data: {e}")
            return None

    @staticmethod
    def export_to_excel(dataframe, filename='asset_data.xlsx'):
        """
        Ekspor DataFrame ke Excel
        """
        try:
            # Simpan ke file Excel
            dataframe.to_excel(filename, index=False)
            return filename
        except Exception as e:
            st.error(f"Gagal mengekspor data: {e}")
            return None

class ReportGenerator:
    @staticmethod
    def generate_summary(dataframe):
        """
        Buat ringkasan dari data aset
        """
        try:
            # Total nilai aset
            total_aset = dataframe['Total Harga'].sum()
            
            # Ringkasan per vendor
            vendor_summary = dataframe.groupby('Vendor')['Total Harga'].sum()
            
            # Ringkasan per jenis satuan
            satuan_summary = dataframe.groupby('Jenis Satuan')['Quantity'].sum()
            
            return {
                'Total Aset': total_aset,
                'Ringkasan Vendor': vendor_summary,
                'Ringkasan Satuan': satuan_summary
            }
        except Exception as e:
            st.error(f"Gagal membuat ringkasan: {e}")
            return None

    @staticmethod
    def visualize_summary(summary):
        """
        Visualisasi ringkasan data
        """
        import matplotlib.pyplot as plt
        import io

        try:
            # Visualisasi ringkasan vendor
            plt.figure(figsize=(10, 5))
            summary['Ringkasan Vendor'].plot(kind='bar')
            plt.title('Total Aset per Vendor')
            plt.xlabel('Vendor')
            plt.ylabel('Total Harga')
            plt.tight_layout()
            
            # Simpan plot ke buffer
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            
            return buffer
        except Exception as e:
            st.error(f"Gagal membuat visualisasi: {e}")
            return None
class AssetTrackingApp:
    def __init__(self):
        # Inisialisasi session state untuk tabel
        if 'asset_table' not in st.session_state:
            st.session_state.asset_table = pd.DataFrame(columns=[
                'Tanggal Beli', 'Nama Item', 'Quantity', 'Jenis Satuan', 'Harga', 'Total Harga', 'Vendor'
            ])
        
        if 'temp_table' not in st.session_state:
            st.session_state.temp_table = pd.DataFrame(columns=[
                'Tanggal Beli', 'Nama Item', 'Quantity', 'Jenis Satuan', 'Harga', 'Total Harga', 'Vendor'
            ])

    def run(self):
        st.title("🧾 Pencatatan Aset Tetap")
        
        # Input API Key
        gemini_api_key = os.getenv('GEMINI_API_KEY')

        # Tab navigasi
        tab1, tab2, tab3 = st.tabs(["Input Data", "Tabel Aset", "Laporan"])

        with tab1:
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

        with tab2:
            self.manage_asset_table()

        with tab3:
            self.generate_reports()

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
            nama_vendor = st.text_input("Vendor")
            
        with col2:
            quantity = st.number_input("Quantity", min_value=0.0, value=1.0, format="%.2f")
            jenis_satuan = st.text_input("Jenis Satuan", placeholder="pcs, kg, meter, dll")
            harga = st.number_input("Harga Satuan", min_value=0.0, value=0.0)

        # Hitung total harga
        total_harga = quantity * harga

        # Validasi input
        input_data = {
            'Nama Item': nama_item,
            'Quantity': quantity,
            'Harga': harga,
            'Vendor': nama_vendor
        }
        validation_errors = DataValidator.validate_input(input_data)

        # Tampilkan hasil
        st.write(f"**Total Harga:** {total_harga}")
        st.write(f"**Vendor:** {nama_vendor}")

        # Tombol tambah ke tabel sementara
        if st.button("Tambah ke Tabel Sementara"):
            # Cek validasi
            if not validation_errors:
                # Tambahkan data ke tabel sementara
                new_data = pd.DataFrame([{
                    'Tanggal Beli': tanggal_beli.strftime('%Y-%m-%d'),
                    'Nama Item': nama_item,
                    'Quantity': quantity,
                    'Jenis Satuan': jenis_satuan,
                    'Harga': harga,
                    'Total Harga': total_harga,
                    'Vendor': nama_vendor
                }])

                st.session_state.temp_table = pd.concat(
                    [st.session_state.temp_table, new_data],
                    ignore_index=True
                )

                st.success("Data berhasil ditambahkan ke tabel sementara!")
            else:
                # Tampilkan error validasi
                for error in validation_errors:
                    st.error(error)

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
                if len(parts) == 7:  # Memastikan ada 7 kolom
                    processed_data.append(parts)
            
            # Buat DataFrame
            if processed_data:
                df = pd.DataFrame(processed_data, columns=[
                    'Tanggal Beli', 'Nama Item', 'Quantity', 'Jenis Satuan', 'Harga', 'Total Harga', 'Vendor'
                ])
                
                # Konversi tipe data dengan error='coerce'
                df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
                df['Harga'] = pd.to_numeric(df['Harga'], errors='coerce')
                df['Total Harga'] = pd.to_numeric(df['Total Harga'], errors='coerce')
                
                # Bersihkan data yang tidak valid
                df = df.dropna()
                
                # Cek apakah dataframe tidak kosong sebelum concat
                if not df.empty:
                    # Gunakan method copy untuk menghindari warning
                    temp_table = st.session_state.temp_table.copy()
                    st.session_state.temp_table = pd.concat([temp_table, df], ignore_index=True)
                    
                    st.success("Hasil analisis berhasil ditambahkan ke tabel sementara!")
                else:
                    st.warning("Tidak ada data yang valid untuk ditambahkan.")
            else:
                st.warning("Tidak ada data yang dapat diproses.")
        except Exception as e:
            st.error(f"Gagal memproses hasil analisis: {e}")

    def manage_asset_table(self):
        st.subheader("Manajemen Tabel Aset")
        
        # Buat dua kolom untuk tabel sementara dan permanen
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Tabel Sementara")
            if st.session_state.temp_table.empty:
                st.warning("Tabel sementara kosong.")
            else:
                # Tampilkan dan edit tabel sementara
                temp_table = st.data_editor(
                    st.session_state.temp_table, 
                    num_rows="dynamic",
                    key="temp_table_editor"
                )
                
                # Update tabel sementara di session state
                st.session_state.temp_table = temp_table
                
                # Tombol hapus tabel sementara
                if st.button("🗑️ Hapus Tabel Sementara", key="delete_temp_table"):
                    # Konfirmasi sebelum menghapus
                    if st.checkbox("Saya yakin ingin menghapus tabel sementara", key="confirm_delete_temp"):
                        # Reset tabel sementara
                        st.session_state.temp_table = pd.DataFrame(columns=[
                            'Tanggal Beli', 'Nama Item', 'Quantity', 'Jenis Satuan', 'Harga', 'Total Harga', 'Vendor'
                        ])
                        st.success("Tabel sementara berhasil dihapus!")
                
                # Tombol untuk menyimpan data ke tabel utama
                if st.button("💾 Simpan ke Tabel Permanen"):
                    if not st.session_state.temp_table.empty:
                        # Gunakan method copy untuk menghindari warning
                        asset_table = st.session_state.asset_table.copy()
                        st.session_state.asset_table = pd.concat(
                            [asset_table, st.session_state.temp_table],
                            ignore_index=True
                        )
                        
                        # Reset tabel sementara
                        st.session_state.temp_table = pd.DataFrame(columns=[
                            'Tanggal Beli', 'Nama Item', 'Quantity', 'Jenis Satuan', 'Harga', 'Total Harga', 'Vendor'
                        ])
                        
                        st.success("Data berhasil disimpan ke tabel permanen!")
                    else:
                        st.warning("Tidak ada data untuk disimpan.")
        
        with col2:
            st.subheader("Tabel Permanen")
            if st.session_state.asset_table.empty:
                st.warning("Tabel permanen kosong.")
            else:
                # Tampilkan dan edit tabel permanen
                asset_table = st.data_editor(
                    st.session_state.asset_table, 
                    num_rows="dynamic",
                    key="permanent_table_editor"
                )
                
                # Update tabel permanen di session state
                st.session_state.asset_table = asset_table
                
                # Tombol hapus tabel permanen
                if st.button("🗑️ Hapus Tabel Permanen", key="delete_permanent_table"):
                    # Konfirmasi sebelum menghapus
                    if st.checkbox("Saya yakin ingin menghapus tabel permanen", key="confirm_delete_permanent"):
                        # Reset tabel permanen
                        st.session_state.asset_table = pd.DataFrame(columns=[
                            'Tanggal Beli', 'Nama Item', 'Quantity', 'Jenis Satuan', 'Harga', 'Total Harga', 'Vendor'
                        ])
                        st.success("Tabel permanen berhasil dihapus!")
                
                # Tombol ekspor data
                col_export1, col_export2 = st.columns(2)
                
                with col_export1:
                    # Ekspor ke CSV
                    if st.button("📄 Ekspor CSV"):
                        filename = ExportService.export_to_csv(st.session_state.asset_table)
                        if filename:
                            st.success(f"Data berhasil diekspor ke {filename}")
                
                with col_export2:
                    # Ekspor ke Excel
                    if st.button("📊 Ekspor Excel"):
                        filename = ExportService.export_to_excel(st.session_state.asset_table)
                        if filename:
                            st.success(f"Data berhasil diekspor ke {filename}")

    def generate_reports(self):
        st.subheader("Laporan Aset")
        
        if st.session_state.asset_table.empty:
            st.warning("Tabel aset kosong. Tambahkan data terlebih dahulu.")
        else:
            summary = ReportGenerator.generate_summary(st.session_state.asset_table)
            st.write("**Total Aset:**", summary['Total Aset'])
            st.write("**Ringkasan Vendor:**")
            st.dataframe(summary['Ringkasan Vendor'])
            st.write("**Ringkasan Satuan:**")
            st.dataframe(summary['Ringkasan Satuan'])

            # Visualisasi
            buffer = ReportGenerator.visualize_summary(summary)
            st.image(buffer, caption="Visualisasi Total Aset per Vendor")

# Menjalankan aplikasi
if __name__ == "__main__":
    app = AssetTrackingApp()
    app.run()
