package microblock

// User — типизированная модель вместо map.
type User struct {
	Name string
}

// NewUser создаёт пользователя.
func NewUser(name string) User {
	return User{Name: name}
}

// DisplayName возвращает имя для интерфейса.
func (u User) DisplayName() string {
	return u.Name
}
