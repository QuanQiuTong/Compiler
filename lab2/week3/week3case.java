public class Person {
    // 成员变量
    String firstName;
    public String lastName;
    public int age;

    // 构造函数
    public Person(String firstName, String lastName, int age) {
        this.firstName = firstName;
        this.lastName = lastName;
        this.age = age;
    }

    // 私有方法
    private int getBirthYear(int currentYear) {
        return currentYear - this.age;
    }
}