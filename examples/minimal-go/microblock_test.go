package microblock

import "testing"

func TestNewUser(t *testing.T) {
	user := NewUser("Ada")
	if user.DisplayName() != "Ada" {
		t.Fatalf("DisplayName = %q, want Ada", user.DisplayName())
	}
}
