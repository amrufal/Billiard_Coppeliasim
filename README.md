# 🎱 Simulasi Billiar dengan CoppeliaSim & Python

Proyek ini adalah simulasi permainan billiar yang dibuat menggunakan **CoppeliaSim EDU** dan bahasa pemrograman **Python**. Komunikasi antara Python dan CoppeliaSim difasilitasi oleh **ZMQ Remote API**, memungkinkan kontrol dan pembacaan data dari lingkungan simulasi secara eksternal.



## 📖 Latar Belakang Proyek

Proyek ini bertujuan sebagai sarana edukasi untuk memahami konsep-konsep berikut:
* **Pembangunan Lingkungan Simulasi**: Cara membangun *scene* di CoppeliaSim.
* **Dinamika Benda Kaku**: Mensimulasikan gerak translasi dan rotasi objek dengan mengabaikan deformasi.
* **Hukum Fisika**: Menerapkan konsep kekekalan energi dan momentum untuk memodelkan tumbukan antar bola.
* **Remote API**: Cara menggunakan ZMQ Remote API untuk menghubungkan program Python dengan CoppeliaSim, yang memungkinkan pengguna membaca informasi *scene* dan memberi perintah secara terprogram.

---

## ✨ Fitur Utama

* **Kontrol Bola Putih**: Pemain dapat menentukan kecepatan dan arah bola putih melalui input di terminal.
* **Mode Penargetan**:
    * **Target Otomatis**: Pilih bola sasaran berdasarkan nama atau jarak terdekat, dan program akan menghitung vektor gaya yang dibutuhkan.
    * **Mode Manual**: Masukkan vektor gaya (`Fx, Fy, Fz`) dan torsi (`Tx, Ty, Tz`) secara langsung untuk kontrol penuh.
* **Aplikasi Gaya & Torsi**: Memberikan gaya pada titik tertentu (offset) relatif terhadap pusat massa bola untuk menciptakan efek putaran (*spin*).
* **Interaksi Berbasis Terminal**: Seluruh input dan *feedback* dari simulasi ditampilkan melalui terminal.

---

## 🛠️ Perangkat Lunak yang Dibutuhkan

Pastikan Anda memiliki perangkat lunak berikut:
1.  **Python 3**: Sebagai bahasa pemrograman dan interpreter.
2.  **CoppeliaSim Edu**: Sebagai perangkat lunak untuk membuat dan menjalankan lingkungan simulasi.
3.  **Pustaka ZMQ Remote API Python**: Untuk menghubungkan script Python ke CoppeliaSim.
    ```bash
    pip install coppeliasim-zmqremoteapi-client
    ```

---

## 🕹️ Tutorial Penggunaan Program

Berikut adalah langkah-langkah untuk menjalankan simulasi permainan billiar ini.

### 1. Persiapan Lingkungan
1.  **Buka CoppeliaSim**: Jalankan perangkat lunak CoppeliaSim.
2.  **Muat Scene**: Buka file *scene* yang berisi meja dan bola-bola billiar (misalnya, yang berisi objek `/Sphere[0]` hingga `/Sphere[6]`).
3.  **Pastikan Simulasi Belum Berjalan**: *Scene* harus dalam keadaan berhenti (*stopped*).

### 2. Menjalankan Program
1.  Buka terminal atau *command prompt*.
2.  Arahkan ke direktori tempat Anda menyimpan file Python proyek ini.
3.  Jalankan file Python utama.
4.  Program akan secara otomatis:
    * Menghubungkan diri ke CoppeliaSim.
    * Mendeteksi semua bola di dalam *scene*.
    * Menampilkan informasi massa dan diameter bola putih.
    * Menampilkan posisi awal semua bola.

### 3. Interaksi Selama Simulasi
Pada setiap giliran, program akan menampilkan pilihan mode bidik di terminal:

* **Mode `target`**:
    1.  Pilih bola sasaran, baik dengan `by_name` (mengetik nama objek bola) atau `nearest` (otomatis memilih bola terdekat).
    2.  Program akan menghitung arah dari bola putih ke target dan menerapkan impuls.
    3.  Anda juga dapat menambahkan *offset* (`rx, ry, rz`) untuk memberikan efek putaran.

* **Mode `manual`**:
    1.  Masukkan komponen gaya (`Fx, Fy, Fz`) dan torsi (`Tx, Ty, Tz`) secara langsung.
    2.  Program akan menanyakan apakah gaya ingin diberikan pada titik *offset*. Jika *offset* melebihi radius bola, nilainya akan otomatis disesuaikan (*clamped*).

Setelah input dimasukkan, program akan menampilkan ringkasan gaya/impuls yang akan diterapkan.

### 4. Fase Gerak Bebas (*Free-Run*)
1.  Setelah gaya diterapkan, simulasi akan dijalankan dalam mode bebas (*free-run*).
2.  Bola akan bergerak sesuai hukum fisika berdasarkan gaya yang diberikan.
3.  Kecepatan bola putih akan dipantau selama beberapa detik (durasi dapat diatur).

### 5. Akhir Giliran
1.  Setelah fase *free-run* selesai, kecepatan semua bola di-reset menjadi nol.
2.  Posisi akhir semua bola akan ditampilkan di terminal.
3.  Program akan menanyakan apakah Anda ingin melanjutkan ke giliran berikutnya.
    * Ketik `y` untuk melanjutkan permainan.
    * Ketik `n` untuk menghentikan permainan.

### 6. Mengakhiri Permainan
Jika Anda memilih `n`, program akan:
1.  Memastikan semua bola benar-benar berhenti.
2.  Menghentikan simulasi di CoppeliaSim.
3.  Menampilkan pesan bahwa permainan telah selesai dan menutup koneksi.
