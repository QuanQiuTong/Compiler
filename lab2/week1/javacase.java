import java.util.Scanner;

public class SimpleJavaExample {
    
    // 主函数
    public static void main(String[] args) {

        int number = 5;
        
        // 函数调用
        boolean isEven = checkEven(number);
        
        // 分支语句
        if(isEven) {
            number = 6;
        } else {
            number = 7;
        }
        
    }
    
    // 检查数字是否为偶数的函数
    public static boolean checkEven(int num) {
        return num % 2 == 0;  // 返回布尔值
    }
    
}