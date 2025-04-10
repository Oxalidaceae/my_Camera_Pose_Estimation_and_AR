import numpy as np
import cv2 as cv

# 입력 정보
video_file = 'data/video.mp4'
K = np.array([[590.46512818, 0., 641.58986121],
              [0., 590.38915726, 365.10676819],
              [0., 0., 1.]])
dist_coeff = np.array([0.00304039, -0.00735964, 0.00019495, 0.00068062, 0.00116275])
board_pattern = (8, 6)
board_cellsize = 0.03
board_flags = cv.CALIB_CB_ADAPTIVE_THRESH + cv.CALIB_CB_NORMALIZE_IMAGE + cv.CALIB_CB_FAST_CHECK

# 체스보드 포인트
obj_points = board_cellsize * np.array(
    [[c, r, 0] for r in range(board_pattern[1]) for c in range(board_pattern[0])]
).astype(np.float32)

# 큐브 정의
cube_pts = np.array([
    [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],  # 바닥
    [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1],  # 천장
], dtype=np.float32)

edges = [
    (0, 1), (1, 2), (2, 3), (3, 0),  # 바닥
    (4, 5), (5, 6), (6, 7), (7, 4),  # 천장
    (0, 4), (1, 5), (2, 6), (3, 7)   # 수직선
]

faces = [
    [0, 1, 2, 3],  # 바닥
    [4, 5, 6, 7],  # 천장
    [0, 1, 5, 4],
    [1, 2, 6, 5],
    [2, 3, 7, 6],
    [3, 0, 4, 7]
]

# === 피라미드 블럭 생성 ===
def generate_pyramid_blocks(base_size, cube_size=1):
    all_blocks = []
    all_colors = []
    base_colors = [
        (255, 100, 100),  # 빨강
        (255, 180, 80),   # 주황
        (255, 255, 100),  # 노랑
        (100, 255, 100),  # 연두
        (100, 200, 255),  # 하늘
        (180, 100, 255),  # 보라
    ]
    for layer in range(base_size):
        side = base_size - layer
        z = -(base_size - 1 - layer)  # 위로 쌓이게
        offset = (base_size - side) / 2
        color = base_colors[layer % len(base_colors)]
        for y in range(side):
            for x in range(side):
                pos = np.array([x + offset, y + offset, z])
                block = cube_pts + pos
                all_blocks.append(block)
                all_colors.append(color)
    return np.vstack(all_blocks) * board_cellsize, all_colors

block_points, block_colors = generate_pyramid_blocks(base_size=5)

# 비디오
video = cv.VideoCapture(video_file)
assert video.isOpened(), 'Cannot open video: ' + video_file

# 저장용 비디오 초기화
fourcc = cv.VideoWriter_fourcc(*'mp4v')
fps = video.get(cv.CAP_PROP_FPS)
width = int(video.get(cv.CAP_PROP_FRAME_WIDTH))
height = int(video.get(cv.CAP_PROP_FRAME_HEIGHT))
out = cv.VideoWriter('data/output.mp4', fourcc, fps, (width, height))

# 메인 루프
while True:
    valid, img = video.read()
    if not valid:
        break

    success, img_points = cv.findChessboardCorners(img, board_pattern, board_flags)
    if success:
        img_points = img_points.reshape(-1, 2).astype(np.float32)
        ret, rvec, tvec = cv.solvePnP(obj_points, img_points, K, dist_coeff)

        projected, _ = cv.projectPoints(block_points, rvec, tvec, K, dist_coeff)
        pts2d = projected.reshape(-1, 2).astype(np.int32)

        overlay = img.copy()
        n_cubes = len(block_points) // 8

        for i in range(n_cubes):
            base = i * 8
            color = block_colors[i]
            pts_cube = pts2d[base:base+8]

            # 반투명 채움
            for face in faces:
                poly = np.array([pts_cube[j] for j in face], dtype=np.int32)
                cv.fillConvexPoly(overlay, poly, color)

        # 반투명 블렌딩
        alpha = 0.4
        cv.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)

        # 테두리 라인 그리기
        for i in range(n_cubes):
            base = i * 8
            pts_cube = pts2d[base:base+8]
            for (start, end) in edges:
                pt1 = pts_cube[start]
                pt2 = pts_cube[end]
                cv.line(img, pt1, pt2, (50, 50, 50), 1)

        # 카메라 위치 표시
        R, _ = cv.Rodrigues(rvec)
        p = (-R.T @ tvec).flatten()
        info = f'XYZ: [{p[0]:.3f} {p[1]:.3f} {p[2]:.3f}]'
        cv.putText(img, info, (10, 25), cv.FONT_HERSHEY_DUPLEX, 0.6, (0, 255, 0))

    cv.imshow('Upsidedown Pyramid', img)
    out.write(img)
    key = cv.waitKey(10)
    if key == ord(' '): key = cv.waitKey()
    if key == 27: break

out.release()
video.release()
cv.destroyAllWindows()