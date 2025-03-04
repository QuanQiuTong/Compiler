public class SimpleTest {

    public static void main(String[] args) {
        // 创建一个新的实例
        SimpleTest test = new SimpleTest();
        
        // 打印结果
        System.out.println("Sum of 2 and 3 is: " + test.add(2, 3));
    }

    // 添加两个整数
    public int add(int a, int b) {
        return a + b;
    }

    // 测试条件语句
    public void testCondition(int x) {
        if (x > 0) {
            System.out.println("Positive number");
        } else if (x < 0) {
            System.out.println("Negative number");
        } else {
            System.out.println("Zero");
        }
    }

    // 测试循环
    public void testLoop() {
        for (int i = 0; i < 5; i++) {
            System.out.println("Loop iteration: " + i);
        }
    }

    // 测试数组操作
    public void testArray() {
        int[] numbers = {1, 2, 3, 4, 5};
        for (int num : numbers) {
            System.out.println("Number: " + num);
        }
    }

    // 测试字符串操作
    public void testString() {
        String message = "Hello, World!";
        System.out.println("Message length: " + message.length());
        System.out.println("Uppercase: " + message.toUpperCase());
    }
}
