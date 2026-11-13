
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

from matplotlib.patches import Ellipse

# -----------------------------------------
# 1. 웹 페이지 기본 설정
# -----------------------------------------

st.set_page_config(
    page_title="Contact Lens Optical Simulator",
    page_icon="👁️",
    layout="wide"
)

# -----------------------------------------
# 비밀번호 인증
# -----------------------------------------

import hmac

def password_check():

    if st.session_state.get("authenticated", False):
        return True

    def password_entered():
        entered_password = st.session_state["password"]

        if hmac.compare_digest(
            entered_password,
            st.secrets["APP_PASSWORD"]
        ):
            st.session_state["authenticated"] = True
            st.session_state.pop("password", None)
            st.session_state["password_error"] = False
        else:
            st.session_state["password_error"] = True

    st.title("콘택트렌즈 시뮬레이터")
    st.subheader("비밀번호를 입력해 주세요.")

    st.text_input(
        "접속 비밀번호",
        type="password",
        key="password",
        on_change=password_entered
    )

    if st.session_state.get("password_error", False):
        st.error("비밀번호가 올바르지 않습니다.")

    return False


if not password_check():
    st.stop()



# 한글 폰트 설정
from matplotlib import font_manager
import os

font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"

if os.path.exists(font_path):
    font_manager.fontManager.addfont(font_path)

    font_name = font_manager.FontProperties(
        fname=font_path
    ).get_name()

    plt.rcParams["font.family"] = font_name
else:
    raise FileNotFoundError(
        f"한글 폰트 파일을 찾을 수 없습니다: {font_path}"
    )

plt.rcParams["axes.unicode_minus"] = False

st.title("콘택트렌즈 광학 시뮬레이터 (대륜 10703 김민찬)")
st.write(
    "콘택트렌즈의 굴절률, 곡률 반경, 두께 및 물체 거리에 따른 "
    "광학적 변화를 관찰하는 2차원 시뮬레이터"
)

st.info(
    "이 시뮬레이터는 콘택트렌즈를 두꺼운 렌즈로 근사하여 계산함. "
    "안구 그림은 구조를 이해하기 위한 개념도이며, 실제 눈 전체의 광학계산을 수행하지는 않음."
)

# -----------------------------------------
# 2. 입력 변수 설정
# -----------------------------------------

st.sidebar.header("렌즈 변수 조절")

n = st.sidebar.slider(
    "렌즈 굴절률 n",
    min_value=1.38,
    max_value=1.50,
    value=1.42,
    step=0.01
)

R1 = st.sidebar.number_input(
    "앞면 곡률 반경 R1 (mm)",
    min_value=1.0,
    max_value=30.0,
    value=8.6,
    step=0.1
)

R2 = st.sidebar.number_input(
    "뒷면 곡률 반경 R2 (mm)",
    min_value=-30.0,
    max_value=-1.0,
    value=-8.0,
    step=0.1
)

t = st.sidebar.slider(
    "렌즈 두께 t (mm)",
    min_value=0.05,
    max_value=0.50,
    value=0.12,
    step=0.01
)

do = st.sidebar.slider(
    "물체 거리 (mm)",
    min_value=100,
    max_value=5000,
    value=1000,
    step=100
)

# 눈물층을 단순화한 주변 매질의 굴절률
n_medium = 1.336

# -----------------------------------------
# 3. 두꺼운 렌즈 광학 계산
# -----------------------------------------

def calculate_lens(n, R1, R2, t, do):

    # 각 렌즈 표면의 굴절력
    phi1 = (n - n_medium) / R1
    phi2 = (n_medium - n) / R2

    # 두꺼운 렌즈의 전체 굴절력
    phi = phi1 + phi2 - (t / n) * phi1 * phi2

    if abs(phi) < 1e-10:
        return None

    # 주변 매질에서의 초점거리
    f = n_medium / phi

    # ABCD 행렬
    S1 = np.array([
        [1, 0],
        [-phi1, 1]
    ])

    T = np.array([
        [1, t / n],
        [0, 1]
    ])

    S2 = np.array([
        [1, 0],
        [-phi2, 1]
    ])

    M = S2 @ T @ S1

    A, B = M[0, 0], M[0, 1]
    C, D = M[1, 0], M[1, 1]

    # 물체 거리와 상거리 계산
    do_reduced = do / n_medium
    denominator = C * do_reduced + D

    if abs(denominator) < 1e-10:
        return None

    di = -n_medium * (
        (A * do_reduced + B) / denominator
    )

    return f, di, phi


# -----------------------------------------
# 4. 안구 및 렌즈 단면 그리기
# -----------------------------------------

def draw_simulation(n, R1, R2, t, do):

    result = calculate_lens(n, R1, R2, t, do)

    if result is None:
        st.error("현재 입력값으로는 계산할 수 없습니다.")
        return

    f, di, phi = result

    # 렌즈 표면의 높이 좌표
    y = np.linspace(-0.65, 0.65, 200)

    # 곡면의 좌표 계산
    def sag(R, y):
        inside = R**2 - y**2
        inside = np.maximum(inside, 0)
        return np.sign(R) * (
            abs(R) - np.sqrt(inside)
        )

    x1 = sag(R1, y)
    x2 = t + sag(R2, y)

    if np.min(x2 - x1) <= 0:
        st.error(
            "렌즈의 앞면과 뒷면이 겹칩니다. "
            "곡률 반경이나 두께를 조절해 주세요."
        )
        return

    fig, ax = plt.subplots(figsize=(12, 6))

    # 안구 외곽
    eye = Ellipse(
        (14, 0),
        width=22,
        height=12,
        facecolor="lightblue",
        edgecolor="steelblue",
        alpha=0.18,
        linewidth=2
    )
    ax.add_patch(eye)

    # 각막
    cornea_y = np.linspace(-2.6, 2.6, 200)
    cornea_x = 3.8 + 0.55 * (
        cornea_y / 2.6
    ) ** 2

    ax.plot(
        cornea_x,
        cornea_y,
        color="royalblue",
        linewidth=3,
        label="각막"
    )

    # 수정체
    crystalline_lens = Ellipse(
        (11, 0),
        width=2.2,
        height=5,
        facecolor="orange",
        edgecolor="darkorange",
        alpha=0.65
    )
    ax.add_patch(crystalline_lens)

    # 망막
    retina_y = np.linspace(-4.7, 4.7, 200)
    retina_x = 23 + 0.25 * (
        retina_y / 4.7
    ) ** 2

    ax.plot(
        retina_x,
        retina_y,
        color="darkred",
        linewidth=3,
        label="망막"
    )

    # 콘택트렌즈 위치
    lens_x1 = 1.0 + x1
    lens_x2 = 1.0 + x2

    ax.fill_betweenx(
        y,
        lens_x1,
        lens_x2,
        color="cyan",
        alpha=0.65,
        label="콘택트렌즈"
    )

    ax.plot(lens_x1, y, color="teal", linewidth=1.5)
    ax.plot(lens_x2, y, color="teal", linewidth=1.5)

    # 광축
    ax.axhline(
        0,
        color="gray",
        linestyle="--",
        linewidth=1
    )

    # 개념적인 광선
    ray_y = [-2, 0, 2]

    for start_y in ray_y:
        ax.plot(
            [-5, 1],
            [start_y, start_y * 0.75],
            color="orange",
            linewidth=1.5
        )

        ax.plot(
            [1.1, 3.8],
            [start_y * 0.75, start_y * 0.45],
            color="orange",
            linewidth=1.5
        )

        ax.plot(
            [4.0, 11, 23],
            [start_y * 0.45, start_y * 0.15, 0],
            color="orange",
            linestyle=":",
            linewidth=1.2
        )

    # 부위 이름 표시
    ax.text(3.5, 3.1, "각막", ha="center", fontsize=11)
    ax.text(11, 3.1, "수정체", ha="center", fontsize=11)
    ax.text(23, 5.1, "망막", ha="center", fontsize=11)
    ax.text(1.5, 1.0, "콘택트렌즈", ha="center", fontsize=10)

    ax.set_title("콘택트렌즈와 안구의 단면도", fontsize=15)
    ax.set_xlabel("가로 방향")
    ax.set_ylabel("세로 방향")

    ax.set_xlim(-6, 28)
    ax.set_ylim(-7, 7)
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)

    st.pyplot(fig)
    plt.close(fig)

    # -------------------------------------
    # 5. 계산 결과 출력
    # -------------------------------------

    st.subheader("광학 계산 결과")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "초점거리",
            f"{f:.2f} mm"
        )

    with col2:
        st.metric(
            "상거리",
            f"{di:.2f} mm"
        )

    with col3:
        st.metric(
            "렌즈 굴절력",
            f"{phi * 1000:.2f} D"
        )

    st.caption(
        "계산은 콘택트렌즈 자체를 대상으로 함. "
        "안구 내부의 광선은 실제 광학계산 결과가 아닌 개념적 표현임."
    )


# -----------------------------------------
# 6. 시뮬레이션 실행
# -----------------------------------------

draw_simulation(n, R1, R2, t, do)
