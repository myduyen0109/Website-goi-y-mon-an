document.addEventListener("DOMContentLoaded", function () {

    // ====================================
    // XỬ LÝ FORM ĐĂNG NHẬP
    // ====================================

    const loginForm = document.getElementById("loginForm");

    if (loginForm) {

        loginForm.addEventListener("submit", function (event) {

            const email =
                document.getElementById("email");

            const password =
                document.getElementById("matkhau");

            const emailError =
                document.getElementById("emailError");

            const passwordError =
                document.getElementById("passwordError");


            // Xóa thông báo cũ
            emailError.textContent = "";
            passwordError.textContent = "";


            let valid = true;


            // ====================================
            // KIỂM TRA EMAIL
            // ====================================

            if (email.value.trim() === "") {

                emailError.textContent =
                    "Vui lòng nhập email.";

                valid = false;

            } else {

                const emailPattern =
                    /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

                if (!emailPattern.test(email.value.trim())) {

                    emailError.textContent =
                        "Email không đúng định dạng.";

                    valid = false;
                }
            }


            // ====================================
            // KIỂM TRA MẬT KHẨU
            // ====================================

            if (password.value.trim() === "") {

                passwordError.textContent =
                    "Vui lòng nhập mật khẩu.";

                valid = false;

            } else if (password.value.length < 6) {

                passwordError.textContent =
                    "Mật khẩu phải có ít nhất 6 ký tự.";

                valid = false;
            }


            // ====================================
            // KHÔNG CHO SUBMIT NẾU DỮ LIỆU SAI
            // ====================================

            if (!valid) {

                event.preventDefault();

                return;
            }


            // ====================================
            // ĐỔI TRẠNG THÁI NÚT
            // ====================================

            const loginButton =
                document.getElementById("loginButton");

            if (loginButton) {

                loginButton.textContent =
                    "Đang đăng nhập...";

                loginButton.disabled = true;
            }

        });
    }


    // ====================================
    // HIỆN / ẨN MẬT KHẨU
    // ====================================

    const togglePassword =
        document.getElementById("togglePassword");

    const passwordInput =
        document.getElementById("matkhau");


    if (togglePassword && passwordInput) {

        togglePassword.addEventListener("click", function () {

            if (passwordInput.type === "password") {

                passwordInput.type = "text";

                togglePassword.textContent = "Ẩn";

            } else {

                passwordInput.type = "password";

                togglePassword.textContent = "Hiện";
            }

        });
    }

});




// ====================================
// XỬ LÝ FORM ĐĂNG KÝ
// ====================================

const registerForm =
    document.getElementById("registerForm");

if (registerForm) {

    registerForm.addEventListener("submit", function (event) {

        const hoten =
            document.getElementById("hoten");

        const email =
            document.getElementById("email");

        const password =
            document.getElementById("registerPassword");

        const confirmPassword =
            document.getElementById("xacnhanmatkhau");


        const nameError =
            document.getElementById("nameError");

        const emailError =
            document.getElementById("registerEmailError");

        const passwordError =
            document.getElementById(
                "registerPasswordError"
            );

        const confirmError =
            document.getElementById(
                "confirmPasswordError"
            );


        // Xóa lỗi cũ

        nameError.textContent = "";

        emailError.textContent = "";

        passwordError.textContent = "";

        confirmError.textContent = "";


        let valid = true;


        // ====================================
        // KIỂM TRA HỌ TÊN
        // ====================================

        if (hoten.value.trim() === "") {

            nameError.textContent =
                "Vui lòng nhập họ và tên.";

            valid = false;
        }


        // ====================================
        // KIỂM TRA EMAIL
        // ====================================

        if (email.value.trim() === "") {

            emailError.textContent =
                "Vui lòng nhập email.";

            valid = false;

        } else {

            const emailPattern =
                /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

            if (
                !emailPattern.test(
                    email.value.trim()
                )
            ) {

                emailError.textContent =
                    "Email không đúng định dạng.";

                valid = false;
            }
        }


        // ====================================
        // KIỂM TRA MẬT KHẨU
        // ====================================

        if (password.value === "") {

            passwordError.textContent =
                "Vui lòng nhập mật khẩu.";

            valid = false;

        } else if (password.value.length < 6) {

            passwordError.textContent =
                "Mật khẩu phải có ít nhất 6 ký tự.";

            valid = false;
        }


        // ====================================
        // KIỂM TRA XÁC NHẬN MẬT KHẨU
        // ====================================

        if (confirmPassword.value === "") {

            confirmError.textContent =
                "Vui lòng xác nhận mật khẩu.";

            valid = false;

        } else if (
            password.value !==
            confirmPassword.value
        ) {

            confirmError.textContent =
                "Mật khẩu xác nhận không khớp.";

            valid = false;
        }


        // ====================================
        // KHÔNG GỬI FORM NẾU CÓ LỖI
        // ====================================

        if (!valid) {

            event.preventDefault();

            return;
        }


        // ====================================
        // ĐỔI NÚT ĐĂNG KÝ
        // ====================================

        const registerButton =
            document.getElementById(
                "registerButton"
            );

        if (registerButton) {

            registerButton.textContent =
                "Đang đăng ký...";

            registerButton.disabled = true;
        }

        // ====================================
// HIỆN / ẨN MẬT KHẨU ĐĂNG KÝ
// ====================================

const toggleRegisterPassword =
    document.getElementById(
        "toggleRegisterPassword"
    );

const registerPassword =
    document.getElementById(
        "registerPassword"
    );


if (
    toggleRegisterPassword &&
    registerPassword
) {

    toggleRegisterPassword.addEventListener(
        "click",
        function () {

            if (
                registerPassword.type ===
                "password"
            ) {

                registerPassword.type =
                    "text";

                toggleRegisterPassword.textContent =
                    "Ẩn";

            } else {

                registerPassword.type =
                    "password";

                toggleRegisterPassword.textContent =
                    "Hiện";
            }

        }
    );
}

    });
}