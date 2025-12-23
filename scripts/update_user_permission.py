#!/usr/bin/env python3
"""
更新用户权限脚本
将指定用户设置为超级用户（管理员）
"""

import asyncio
import sys
from pymongo import MongoClient
from app.core.config import settings


async def update_user_to_admin(username: str):
    """
    将用户设置为超级用户

    Args:
        username: 用户名
    """
    try:
        # 连接到MongoDB
        client = MongoClient(settings.MONGO_URI)
        db = client[settings.MONGO_DB]

        # 查找用户
        user = db.users.find_one({"username": username})

        if not user:
            print(f"❌ 用户 '{username}' 不存在")
            return False

        print(f"🔍 找到用户: {user['username']}")
        print(f"📧 邮箱: {user['email']}")
        print(f"🔐 当前管理员权限: {'是' if user.get('is_admin', False) else '否'}")

        # 更新用户权限
        result = db.users.update_one(
            {"username": username},
            {"$set": {"is_admin": True}}
        )

        if result.modified_count > 0:
            print(f"✅ 用户 '{username}' 已成功设置为超级用户")

            # 验证更新
            updated_user = db.users.find_one({"username": username})
            print(f"🔐 更新后管理员权限: {'是' if updated_user.get('is_admin', False) else '否'}")

            # 显示所有用户列表和权限状态
            print("\n📋 所有用户列表:")
            users = db.users.find({}, {"username": 1, "email": 1, "is_admin": 1, "created_at": 1})
            for user_data in users:
                admin_status = "管理员" if user_data.get('is_admin', False) else "普通用户"
                print(f"  - {user_data['username']} ({user_data['email']}) - {admin_status}")

            return True
        else:
            print(f"⚠️ 用户 '{username}' 已经是管理员或更新失败")
            return False

    except Exception as e:
        print(f"❌ 更新用户权限失败: {e}")
        return False
    finally:
        client.close()


async def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("使用方法: python scripts/update_user_permission.py <用户名>")
        print("示例: python scripts/update_user_permission.py admin")
        sys.exit(1)

    username = sys.argv[1]

    print(f"🚀 开始更新用户 '{username}' 的权限...")

    success = await update_user_to_admin(username)

    if success:
        print("\n🎉 权限更新完成！该用户现在可以:")
        print("  - 查看系统设置页面")
        print("  - 管理其他用户")
        print("  - 访问管理员功能")
        print("  - 查看系统监控信息")
        print("\n💡 提示: 请让用户重新登录以刷新权限")
    else:
        print("\n❌ 权限更新失败")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())