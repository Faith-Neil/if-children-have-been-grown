# 为什么有这个文件：把关演示的页面和单进程后台打成同一份镜像。
# 它解决什么问题：公司虚拟机上不跑 Vite 开发服务，也不把依赖装进业务仓库。
FROM node:24-bookworm-slim AS web
WORKDIR /src/frontend/web
RUN corepack enable && corepack prepare pnpm@11.20.0 --activate
COPY frontend/web/package.json frontend/web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/web ./
ENV VITE_DEMO=0
RUN pnpm build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ICG_REQUIRE_MYSQL=1 \
    ICG_ALLOW_DEMO_LOGIN=0
WORKDIR /opt/icg
# Word 招标文件要先转成 PDF，RAGFlow DeepDOC 才按页识别。镜像里用 LibreOffice，不依赖宿主机上的 Word。
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*
COPY backend/bid-core/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY backend/bid-core /opt/icg/backend/bid-core
COPY --from=web /src/frontend/web/dist /opt/icg/frontend/web/dist
COPY deploy/entrypoint.sh /opt/icg/entrypoint.sh
RUN sed -i 's/\r$//' /opt/icg/entrypoint.sh && chmod +x /opt/icg/entrypoint.sh
EXPOSE 8710
ENTRYPOINT ["/opt/icg/entrypoint.sh"]
