#!/usr/bin/env bash
# Tạo nội dung trang GitHub Release cho 1 tag.
#
#   bash .github/scripts/release_notes.sh v2.7.0 > release_notes.md
#
# - "What's New": lấy từ NỘI DUNG TAG (annotated tag). Viết changelog khi tạo tag:
#       git tag -a v2.7.0 -F changelog.md      (hoặc: git tag -a v2.7.0, rồi gõ trong editor)
#   Dòng đầu tiên của tag là tiêu đề ngắn, các dòng sau là chi tiết (Markdown).
# - "Các thay đổi": tự liệt kê commit từ tag trước tới tag này (bỏ merge & commit bump version).
# - Link "Full Changelog" so sánh với tag trước.
set -euo pipefail

TAG="${1:?Cách dùng: release_notes.sh <tag>}"
REPO="${GITHUB_REPOSITORY:-$(git remote get-url origin 2>/dev/null | sed -E 's#.*github.com[:/]##; s#\.git$##')}"

PREV_TAG="$(git describe --tags --abbrev=0 --match 'v*' "${TAG}^" 2>/dev/null || true)"

# Nội dung tag (chỉ khi là annotated tag; tag nhẹ thì %(contents) chính là commit message → bỏ qua)
TAG_NOTES=""
if [ "$(git cat-file -t "$TAG" 2>/dev/null)" = "tag" ]; then
    TAG_NOTES="$(git tag -l --format='%(contents)' "$TAG" | sed '/-----BEGIN PGP SIGNATURE-----/,$d')"
fi

if [ -n "$PREV_TAG" ]; then
    RANGE="${PREV_TAG}..${TAG}"
else
    RANGE="$TAG"
fi
COMMITS="$(git log "$RANGE" --no-merges --format='- %s (%h)' | grep -viE '^- chore\(release\)' || true)"

cat <<EOF
## 🚀 Floating Clock Release ${TAG} ( •̀ ω •́ )✧

### 📦 Tải về:
- **\`FloatingClock_Setup_${TAG}.exe\`** (khuyên dùng): bộ cài đặt Windows, tạo lối tắt Desktop & Start Menu.
- **\`FloatingClock_Portable_${TAG}.zip\`**: bản chạy ngay không cần cài — giải nén **cả thư mục** rồi chạy \`FloatingClock.exe\` (thư mục \`app\\bin\` chứa trình phát video YouTube).

---

EOF

if [ -n "$TAG_NOTES" ]; then
    echo "### ✨ Có gì mới:"
    echo
    echo "$TAG_NOTES"
    echo
fi

if [ -n "$COMMITS" ]; then
    echo "### 📝 Các thay đổi${PREV_TAG:+ kể từ ${PREV_TAG}}:"
    echo
    echo "$COMMITS"
    echo
fi

if [ -n "$PREV_TAG" ] && [ -n "$REPO" ]; then
    echo "**Full Changelog**: https://github.com/${REPO}/compare/${PREV_TAG}...${TAG}"
    echo
fi

cat <<'EOF'
---

### 🌟 Tính năng chính:
- 🕒 **Đồng hồ nổi luôn trên cùng:** đồng hồ, đếm ngược tan làm, Timer, Stopwatch, Pomodoro, báo thức, nhắc uống nước.
- 📺 **Xem YouTube ngay trên đồng hồ:** dán link (video / playlist / Mix), giữ chuột ~3s để hiện video, rời chuột thì tự ẩn & tạm dừng; có thanh điều khiển kiểu YouTube.
- 💸 **Lương realtime:** tiền lương nhảy từng giây, tăng ca theo phiên, ước tính BHXH, thống kê chi tiết.
- 🐱 **Thú cưng Pixel Cat:** tự đổi trạng thái theo giờ làm, giờ nghỉ trưa và lúc sắp tan làm.
- 🎧 **Âm thanh tập trung:** mưa, sóng biển, quán cafe, rừng đêm, white noise.
- 🌦️ **Thời tiết & hệ thống:** dự báo Open-Meteo, theo dõi CPU / RAM.
- 🎛️ **Bảng điều khiển & phím tắt:** `F8` xuyên chuột, `F9` bật/tắt âm thanh.

### 📖 Tài liệu:
EOF
echo "- [README](https://github.com/${REPO}#readme)"
