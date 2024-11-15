import threading
from my_threading.thread_tasks import thread1


def main():
    results = [None] * 3
    threads = []
    shared_string = [None] * 3
    thr_mutex = [False] * 3

    # 创建并启动三个线程
    for i in range(3):
        thread = threading.Thread(target=thread1, args=(shared_string, results, i, thr_mutex))
        threads.append(thread)
        thread.start()

    while True:
        for i in range(3):
            temp = input(f"对第{i}个线程：")
            shared_string[i] = temp
        print(f"buffer内字符串：{shared_string}")

        thr_mutex[:] = [True] * 3

        for i, result in enumerate(results):
            if result is not None:
                print(f"线程 {i} 的结果: {result}")


if __name__ == "__main__":
    main()
