# BUTO IJO 🌿

Dashboard Streamlit untuk meninjau **potensi greenwashing** pada Sustainability Report dengan checkpoint IndoBERT lokal. PDF, DOCX, TXT, dan input manual didukung. Tidak ada retraining, LLM API, model pengganti, ataupun prediksi acak.

## Menjalankan di Windows

Gunakan Python 3.11 atau 3.12, disarankan RAM minimal 4 GB tersedia; dokumen panjang membutuhkan tambahan memori dan waktu CPU. Dari root repository:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

Jika aktivasi PowerShell dibatasi, jalankan tanpa mengubah execution policy:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

`requirements.lock.txt` merekam versi lengkap environment Windows/Python 3.12 yang telah diuji. Untuk mereproduksi environment tersebut, gunakan `python -m pip install -r requirements.lock.txt`.

Aplikasi tersedia di `http://localhost:8501`. Dependensi hanya perlu diunduh saat instalasi. Parsing dan inference berjalan lokal pada server aplikasi; `local_files_only=True` dan `trust_remote_code=False` mencegah unduhan model dan eksekusi kode checkpoint. `training_args.bin` tidak pernah dibaca/dideserialisasi.

## Lokasi model

Repository menyertakan checkpoint asli di lokasi berikut. Bobot `model.safetensors` dikelola melalui Git LFS agar dapat dimuat langsung oleh Streamlit Community Cloud:

```text
_models/BUTO_IJO_v4_IndoBERT
```

Jika folder tersebut tidak ada pada instalasi Windows, aplikasi memakai lokasi lokal berikut sebagai fallback:

```text
E:\Downloads\Buto Ijo\_models
```

Folder checkpoint harus berisi `config.json`, `model.safetensors`, berkas tokenizer, dan sebaiknya `buto_ijo_v4_metadata.json`. Path juga dapat menunjuk ke direktori induk yang mempunyai **tepat satu** subfolder checkpoint.

Override sebelum memulai server:

```powershell
$env:BUTO_IJO_MODEL_PATH = 'E:\Downloads\Buto Ijo\_models'
streamlit run app.py
```

Jika folder tidak ada, checkpoint rusak/tidak lengkap, atau label tidak dapat dipastikan, aplikasi menampilkan error dan membatalkan inference. Tidak ada fallback. Setelah mengganti bobot atau path, restart proses Streamlit agar resource cache dibersihkan.

Pada Linux dan Streamlit Community Cloud, default selalu menunjuk ke checkpoint di dalam repository. Override berbentuk path absolut Windows diabaikan pada Linux agar tidak berubah menjadi path rusak seperti `/mount/src/.../E:\Downloads\...`. Hapus secret lama tersebut jika pernah ditambahkan. Pastikan Git LFS terpasang ketika melakukan clone manual (`git lfs pull`); Community Cloud mengambil objek LFS secara otomatis.

## Label model yang diverifikasi

Config dan metadata lokal menyatakan:

| Index | Label asli | Tampilan aplikasi | Definisi metadata |
|---|---|---|---|
| 0 | Lower Risk | Low Indication | Evidence score 5–10 |
| 1 | Higher Risk | Potential Greenwashing | Evidence score 0–4 |

Mapping ini **dibaca saat runtime**, bukan diasumsikan dari index 1. `resolve_label_mapping()` memeriksa `id2label`, `label2id`, dan mapping metadata bila ada. Konflik atau label generik tanpa arti yang eksplisit menghentikan inference. Checkpoint lain dengan urutan label terbalik tetap didukung.

Checkpoint ini memiliki field warisan `_num_labels: 5`; mapping aktif berisi dua kelas dan tensor `classifier.weight` berukuran `[2, 768]`, dengan bias `[2]`. Loader memvalidasi dimensi bobot serta `model.config.num_labels`, lalu menolak missing/mismatched weights agar classifier baru yang belum dilatih tidak dipakai. Berkas asli tidak dimodifikasi.

Model dasar dari metadata adalah `indobenchmark/indobert-base-p1`. Dataset berisi 915 pseudo/silver labels (627 train, 139 validation, 149 test), berasal dari konsensus Rule + Qwen + Kimi. Tidak diasumsikan ada human gold standard. **Model mempelajari risiko kecukupan bukti pada klaim lingkungan**, bukan pembuktian kesalahan perusahaan. Tidak ada accuracy/F1 yang dibuat jika tidak ada di metadata.

Metadata mencatat `best_validation_threshold ≈ 0.36`; aplikasi memulai pada **0.50**, sesuai spesifikasi. Nilai metadata ditampilkan sebagai informasi, bukan otomatis diterapkan. Threshold tersebut tidak membuktikan kalibrasi probabilitas di data baru.

## Alur penggunaan

1. Buka **Analisis Dokumen**, lalu unggah PDF/DOCX/TXT. Metadata dan parsing awal tidak menjalankan model.
2. Tekan **Analisis Dokumen**. Progress menunjukkan ekstraksi, segmentasi, batch IndoBERT, dan agregasi.
3. Tinjau KPI, Risk Index, distribusi, ringkasan berbasis aturan, tabel klaim, serta lima klaim berprobabilitas tertinggi.
4. Ubah threshold, filter, pencarian, atau sorting. Seluruh operasi ini memakai probabilitas yang sudah tersimpan; model tidak dipanggil kembali.
5. Unduh seluruh hasil dengan threshold aktif sebagai CSV dan ringkasan JSON. Filter tampilan tidak mengurangi cakupan ekspor.
6. **Uji Teks Cepat** memprediksi satu input kalimat/paragraf sebagai satu unit. **Riwayat** menyimpan snapshot analisis dokumen selama session berjalan.

Data dokumen dan hasil disimpan di memori session, tanpa database atau penyimpanan upload ke disk. Memuat ulang koneksi browser/server dapat menghapus riwayat; ekspor hasil yang perlu disimpan. Model/tokenizer dicache dengan `st.cache_resource`, sementara hasil dokumen tetap terpisah per session. Lock per model mencegah batch dari beberapa session memakai model bersama secara bersamaan.

## Parsing dan batasan input

- **PDF:** PyMuPDF, nomor halaman fisik satu-based dipertahankan termasuk halaman tanpa teks. Nomor cetak pada laporan dapat berbeda. PDF berpassword harus dibuka proteksinya dahulu. Untuk PDF scan tanpa text layer, aplikasi menampilkan: “Dokumen tampaknya berupa hasil scan dan tidak memiliki text layer. OCR belum dijalankan pada versi ini.” PDF campuran hanya menganalisis bagian yang mempunyai text layer.
- **DOCX:** python-docx, paragraf dan tabel diurutkan sesuai isi dokumen. Pagination Word tidak dapat dihitung tanpa layout engine; nilai internal `page=1` berarti satu unit dokumen, bukan klaim lokasi halaman cetak.
- **TXT:** UTF-8 ketat, BOM diperbolehkan. Nilai internal `page=1` adalah satu unit dokumen.
- Cleaning hanya whitespace, soft hyphen akibat line wrap, dan margin pendek yang berulang. Tanda baca, angka, persentase, satuan, kapitalisasi, dan kata dipertahankan. Lowercasing tokenizer mengikuti konfigurasi tokenizer asli.
- Segmentasi menggunakan heuristik kalimat/paragraf/bullet; melindungi desimal, singkatan umum, dan URL. Minimum 25 karakter. Tidak ada stemming atau stopword removal.
- Seluruh kalimat yang memenuhi batas segmentasi dianalisis. Tidak ada classifier relevansi lingkungan tambahan; teks sosial, tata kelola, tabel, atau prosa umum dapat berada di luar cakupan training. Tinjau klaim dan konteks aslinya sebelum menarik kesimpulan. Kalimat lintas halaman dan laporan multi-kolom dapat tersegmentasi kurang sempurna.
- Token dibatasi maksimum 512 termasuk special tokens; input panjang ditruncate sesuai spesifikasi dan jumlah klaim terpotong ditampilkan. Prediction tidak mencakup teks setelah batas ini.

## Risk Index dan confidence

Semua definisi agregasi ada di `core/risk.py`:

```text
flagged = greenwashing_probability >= threshold
mean_probability = rata-rata probabilitas Higher Risk seluruh klaim
flagged_ratio = jumlah flagged / jumlah seluruh klaim
high_confidence_flagged_ratio = jumlah flagged dengan probability >= 0.80 / jumlah seluruh klaim

risk_score = 100 × (0.50 × mean_probability
                 + 0.35 × flagged_ratio
                 + 0.15 × high_confidence_flagged_ratio)
```

Rentang kontinu: **LOW ≤30**, **MODERATE >30 sampai 60**, **HIGH >60**. Skor tidak dibulatkan sebelum menentukan kategori, sehingga nilai pecahan tidak jatuh pada celah kategori. Risk Index merupakan agregasi claim-level predictions dan bukan kelas langsung dari model. Ini bukan probabilitas perusahaan melakukan greenwashing.

Softmax dihitung dari `model(**inputs).logits` menggunakan `torch.softmax(..., dim=-1)` di dalam `torch.no_grad()`, dengan `model.eval()` dan device CUDA jika tersedia, atau CPU. Tidak ada skor berbasis kata kunci untuk menggantikan model.

**Confidence** adalah probabilitas kelas yang dipilih threshold aktif; pada threshold khusus nilainya bisa kurang dari 50%. Probabilitas kedua kelas tetap tidak berubah ketika threshold diubah. Confidence bukan jaminan akurasi empiris atau bukti kalibrasi. Ringkasan JSON mencatat threshold dan komponen agregasi; snapshot riwayat mempertahankan threshold ketika analisis disimpan.

CSV memiliki kolom `claim_id,page,claim,prediction,greenwashing_probability,confidence`, encoding UTF-8 BOM. Teks yang dapat diinterpretasikan spreadsheet sebagai formula diberi apostrof pelindung; angka probabilitas tetap numerik.

## Konfigurasi

| Environment variable | Default | Kegunaan |
|---|---|---|
| `BUTO_IJO_MODEL_PATH` | Checkpoint repository pada Linux; checkpoint repository atau `E:\Downloads\Buto Ijo\_models` pada Windows | Override lokasi checkpoint lokal |
| `BUTO_IJO_BATCH_SIZE` | `16` | Klaim per batch; turunkan jika kehabisan memori |
| `BUTO_IJO_MAX_LENGTH` | `512` | Maksimum token (8–512, dibatasi juga kapasitas model) |
| `BUTO_IJO_MIN_CHAR_LENGTH` | `25` | Batas minimum karakter klaim |
| `BUTO_IJO_MAX_UPLOAD_MB` | `50` | Batas file aplikasi (1–200 MB) |
| `BUTO_IJO_TORCH_THREADS` | Maks. `4` | Thread PyTorch CPU (1–64) |

Upload juga tunduk pada `server.maxUploadSize` di `.streamlit/config.toml`; gunakan nilai server setidaknya sebesar batas aplikasi jika menaikkan batas. Paket PyTorch standar yang dipasang di komputer ini dapat berupa build CPU. Untuk CUDA, pasang build PyTorch resmi yang sesuai driver GPU; aplikasi otomatis memilih CUDA ketika `torch.cuda.is_available()` bernilai true. Tidak diperlukan CUDA untuk memakai model.

Untuk deployment bersama, jalankan di belakang reverse proxy dengan TLS, autentikasi, batas resource, serta pengaturan akses organisasi. Versi ini tidak menyediakan akun pengguna, antrean distributed, database, maupun OCR. Server default lokal menghindari publikasi data dokumen tanpa sengaja.

## Struktur

```text
app.py                  # Entrypoint dan navigasi
components/             # Sidebar, CSS, cards, Plotly charts
pages/                  # Analisis, uji teks, riwayat, tentang model
core/model.py           # Pemeriksaan checkpoint, mapping, resource cache
core/inference.py       # Batch softmax dan orkestrasi dokumen
core/document_parser.py # PDF/DOCX/TXT
core/preprocessing.py   # Cleaning ringan dan segmentasi
core/risk.py            # Threshold dan formula agregasi
core/export.py          # CSV/JSON
core/settings.py        # Konfigurasi environment
tests/                  # Unit, integrasi model asli, dan UI
.streamlit/config.toml  # Tema dan server
requirements.txt        # Dependensi runtime
```

Letakkan logo pilihan Anda di `assets/logo.png` untuk mengganti identitas fallback tanpa mengubah kode.

## Validasi

```powershell
python -m compileall -q app.py core components pages tests
python -m unittest discover -s tests -v
$env:BUTO_IJO_RUN_MODEL_TESTS = '1'
python -m unittest discover -s tests -v
```

Tes integrasi memerlukan checkpoint lokal dan menguji probabilitas terhadap softmax forward pass model sebenarnya, konsistensi single/batch, cache, dan mode evaluasi. Nilai sintetis hanya digunakan sebagai input tes formula matematika, bukan prediksi aplikasi. Tidak ada retraining selama pengujian.

Validasi pada 8 September 2026: 45 pengujian lulus, termasuk 9 pengujian UI Streamlit. Checkpoint asli berhasil dimuat dengan PyTorch 2.10.0 CPU dan Transformers 4.57.6. Uji browser mencakup upload PDF tiga halaman (satu halaman tanpa teks), analisis sepuluh kalimat dengan model asli, dashboard hasil, dan tombol unduh CSV. Ini merupakan pengujian fungsional; belum merupakan load test multiuser atau benchmark laporan 300 halaman.

Debugging akhir pada 12 September 2026: **61 pengujian lulus** dengan integration test model asli diaktifkan. Perbaikan mencakup:

- Threshold dan draft teks tetap tersimpan saat berpindah langsung antara Beranda, Analisis Dokumen, dan Uji Teks Cepat. Navigasi tidak menjalankan inference ulang atau mengubah Risk Index tanpa perubahan threshold.
- Analisis baru mengosongkan pencarian dan filter dokumen sebelumnya.
- Batas paragraf, bullet Word, dan baris tabel DOCX dipertahankan meskipun tidak diakhiri tanda titik.
- Index label menolak boolean, pecahan, dan string yang tidak valid; mapping checkpoint asli tetap 0 = Lower Risk dan 1 = Higher Risk.
- Status sidebar langsung mencerminkan kegagalan pemuatan model dan pulih setelah percobaan yang berhasil.
- Ketika unggahan baru gagal dibaca, hasil yang tersimpan tetap diberi keterangan sebagai hasil dokumen sebelumnya.

Log pengujian lokal: `tests/final_debug_validation.log` (diabaikan Git). Traceback bertanda pengujian penanganan error pada log berasal dari tes yang sengaja mensimulasikan kegagalan pemuatan, bukan kegagalan pengujian. Bobot checkpoint tidak diubah.

Referensi API: [Transformers model loading](https://huggingface.co/docs/transformers/v4.57.1/en/main_classes/model), [Streamlit resource cache](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_resource), [Streamlit navigation](https://docs.streamlit.io/develop/api-reference/navigation/st.navigation).

**BUTO IJO merupakan alat bantu analisis berbasis AI. Hasil prediksi tidak menggantikan audit independen, verifikasi regulator, maupun penilaian ahli.**
